from google import genai
import os
import glob

client = genai.Client(api_key="")

input_dir = './data/DZ/segments'
output_dir = './Gemini/results/DZ'
os.makedirs(output_dir, exist_ok=True)

input_files = glob.glob(os.path.join(input_dir, '*.wav'))
total_files = len(input_files)

for i, input_file in enumerate(input_files, 1):
    print(f"Processing file {i}/{total_files}: {input_file}")
    
    output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}.txt")
    
    # Skip if the output file already exists
    if os.path.exists(output_file):
        print(f"Skipping: {output_file} already exists.")
        continue

    try:
        # Attempt to upload and process the file
        myfile = client.files.upload(file=input_file)

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                'Generate a transcript of the speech.',
                myfile,
            ]
        )
        
        # Write the result to a file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"Successfully processed: {output_file}")

    except Exception as e:
        # If any error occurs, skip this file and print the error
        print(f"Failed to process {input_file}. Error: {e}")
        continue

    # Print progress percentage
    progress = (i / total_files) * 100
    print(f"Progress: {progress:.2f}%")

print("All files processed.")
