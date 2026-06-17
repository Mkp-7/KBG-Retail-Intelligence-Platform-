# Data Setup

## Yelp Open Dataset

Free for educational and personal use. Contains 6.9 million reviews across 150,000+ businesses.

### Download
1. Go to: https://www.yelp.com/dataset
2. Click "Download Dataset" — free Yelp account required
3. Download the TAR file (~4.35 GB compressed, ~8.65 GB extracted)

### Extract (Mac / Linux)
```bash
tar -xf yelp_dataset.tar
```

### Extract (Windows)
Use 7-Zip: https://www.7-zip.org/

### Place in this folder
```
data/
  yelp_academic_dataset_business.json
  yelp_academic_dataset_review.json
```

### Run the extractor
```bash
python module1_voice_of_customer/01_extract_reviews.py
```

Output files (small, safe to commit to GitHub):
- `data/businesses.csv`
- `data/reviews.csv`

The extractor reads the large JSON files line-by-line so it works on any machine regardless of RAM. Takes about 5–10 minutes.
