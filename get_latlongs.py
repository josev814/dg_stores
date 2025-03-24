import os
import requests
import zipfile
import csv

# URL for the ZIP file containing the data
zip_url = 'https://download.geonames.org/export/zip/US.zip'
zip_filename = 'US.zip'
extracted_filename = 'US.txt'
output_file = 'zipcode_locations.csv'


# Function to download the ZIP file
def download_zip(url, filename):
    print(f"Downloading {url}...")
    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)
    print("Download complete.")


# Function to extract the ZIP file
def extract_zip(zip_filename, extract_to):
    print(f"Extracting {zip_filename}...")
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")


# Function to reformat the data
def reformat_zipcode_data(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = infile.readlines()
        writer = csv.writer(outfile)
        
        # Write header to the CSV
        writer.writerow(['zipcode', 'latitude', 'longitude', 'city', 'state'])
        
        for line in reader:
            parts = line.split('\t')
            if len(parts) >= 10:
                # country_code = parts[0]
                zipcode = parts[1]
                city = parts[2]
                # state_full = parts[3]
                state_abbr = parts[4]
                latitude = parts[9]
                longitude = parts[10]
                
                # Write the reformatted data to CSV
                writer.writerow([zipcode, latitude, longitude, city, state_abbr])


def clean_up(zip_filename, extracted_filename):
    print("Cleaning up...")
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        for entry in zip_ref.namelist():
            if os.path.exists(entry):
                os.remove(entry)
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    print("Cleanup complete.")


def main():
    download_zip(zip_url, zip_filename)
    extract_zip(zip_filename, '.')
    reformat_zipcode_data(extracted_filename, output_file)
    clean_up(zip_filename, extracted_filename)


if __name__ == "__main__":
    main()
