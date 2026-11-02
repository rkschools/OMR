import os
from pdf_generator import PDFGenerator
import json

with open('rise_omr_template.json', 'r') as f:
    config = json.load(f)

path = os.path.join(os.getcwd(), 'output', 'RISE_2027_OMR_Final_50Q.pdf')
gen = PDFGenerator(config_dict=config, output_path=path)
gen.generate()
print(f"Generated PDF to {path}")
