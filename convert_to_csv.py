import csv

def convert_to_csv(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        csv_writer = csv.writer(outfile)
        
        for line in infile:
            # Strip whitespace and split the line by tabs or multiple spaces
            row = line.strip().split()
            if len(row) == 8:  # Ensure we have the correct number of columns
                csv_writer.writerow(row)

if __name__ == "__main__":
    convert_to_csv('matches.txt', 'matches.csv')
    print("Conversion complete. Data saved to matches.csv")