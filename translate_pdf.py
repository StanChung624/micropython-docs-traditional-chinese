import os
import argparse
import json
import time
import pymupdf4llm
from google import genai
from google.genai import types
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SOURCE_CHUNKS_FILE = "source_chunks.json"
TRANSLATION_PROGRESS_FILE = "translation_progress.json"

def get_api_key():
    """Fetches the Gemini API key from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set in .env.")
    return api_key

def setup_client():
    """Configures the Gemini client."""
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    return client

def translate_text(text, client, system_instruction):
    """Translates text with retries for rate limits."""
    if not text.strip():
        return ""

    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                ),
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = (2 ** attempt) + 1
                print(f"\nRate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"\nAn error occurred during translation: {e}")
                return f"[Translation Error: {e}]"
    return "[Translation Error: Max retries exceeded]"

def load_json(file_path):
    """Loads a JSON file, returning an empty dict if it doesn't exist."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json(file_path, data):
    """Saves data to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Two-step PDF to Translated Markdown using Gemini API.")
    parser.add_argument("pdf_path", nargs="?", help="The path to the PDF file (required for extraction).")
    parser.add_argument("--output", "-o", default="translated_output.md", help="The final output Markdown file.")
    parser.add_argument("--extract-only", action="store_true", help="Only extract Markdown from PDF and exit.")
    parser.add_argument("--limit", type=int, help="Limit the number of pages to translate (for testing).")
    args = parser.parse_args()

    # Step 1: Extraction
    source_chunks = load_json(SOURCE_CHUNKS_FILE)
    if not source_chunks:
        if not args.pdf_path:
            print("Error: pdf_path is required for the first run (extraction phase).")
            return
        
        if not os.path.exists(args.pdf_path):
            print(f"Error: The file '{args.pdf_path}' was not found.")
            return

        print(f"Step 1: Extracting Markdown from '{args.pdf_path}'...")
        # pymupdf4llm.to_markdown returns a list of dictionaries if page_chunks=True
        pages = pymupdf4llm.to_markdown(args.pdf_path, page_chunks=True)
        
        # We store as a dict for easier indexing
        source_chunks = {str(i+1): page_data.get("text", "") for i, page_data in enumerate(pages)}
        save_json(SOURCE_CHUNKS_FILE, source_chunks)
        print(f"Extraction complete. {len(source_chunks)} pages saved to '{SOURCE_CHUNKS_FILE}'.")
        
        if args.extract_only:
            return

    # Step 2: Translation
    if args.extract_only:
        return

    progress = load_json(TRANSLATION_PROGRESS_FILE)
    client = setup_client()

    system_instruction = (
        "You are a professional technical translator specializing in MicroPython and embedded systems. "
        "Translate the following documentation from English to Traditional Chinese (繁體中文). "
        "Strictly follow these rules:\n"
        "1. DO NOT translate code blocks, inline code, function names, variable names, module names, or file paths.\n"
        "2. Preserve all technical terms and proper nouns in English (e.g., MicroPython, GPIO, ADC, PWM, SPI, I2C, REPL, machine, bool, int, float, array, socket, hardware, peripheral).\n"
        "3. Only translate the explanatory text, comments, and general descriptive sentences.\n"
        "4. Maintain the Markdown formatting exactly as provided (headers, lists, tables, bold text, etc.).\n"
        "5. Ensure the translated text is natural for developers in Taiwan/Hong Kong using Traditional Chinese."
    )

    total_pages = len(source_chunks)
    
    # Ensure keys are processed in order
    sorted_keys = sorted(source_chunks.keys(), key=int)
    
    # Apply limit if specified
    if args.limit:
        sorted_keys = sorted_keys[:args.limit]
        print(f"Step 2: Translating first {len(sorted_keys)} pages (limited)...")
    else:
        print(f"Step 2: Translating {total_pages} pages...")
    
    # Identify pages that need translation (retry errors)
    for key in list(progress.keys()):
        if "[Translation Error" in str(progress[key]):
            del progress[key]

    pbar = tqdm(total=len(sorted_keys), desc="Translating")
    
    for page_key in sorted_keys:
        if page_key in progress:
            pbar.update(1)
            continue
        
        text_to_translate = source_chunks[page_key]
        translated_text = translate_text(text_to_translate, client, system_instruction)
        
        progress[page_key] = translated_text
        save_json(TRANSLATION_PROGRESS_FILE, progress)
        pbar.update(1)

    pbar.close()

    # Final Assembly
    print(f"Final Step: Assembling '{args.output}'...")
    with open(args.output, "w", encoding="utf-8") as out_file:
        for page_key in sorted_keys:
            content = progress.get(page_key, "")
            out_file.write(content)
            out_file.write("\n\n---\n\n")

    print(f"Done! Final translation saved to '{args.output}'.")

if __name__ == "__main__":
    main()
