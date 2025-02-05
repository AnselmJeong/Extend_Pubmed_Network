## Article Class Properties

The `Article` class provides access to:

- `pmid`: PubMed ID
- `related`: Dictionary containing:
  - `pubmed`: Related articles
  - `citedin`: Articles citing this paper
  - `refs`: References cited by this paper
- `bib`: (When `include_bib=True`) Dictionary containing:
  - `authors_str`: Author string
  - `title`: Article title
  - `doi`: Digital Object Identifier
  - `year`: Publication year
  - `journal`: Journal name
  - `keywords`: Article keywords
  - `abstract`: Article abstract

## Error Handling

The module includes robust error handling with exponential backoff:
- Automatic retries for failed requests
- Configurable maximum retry attempts
- Rate limiting to prevent API throttling
- Progress bars for long operations

## Cache

Article data is automatically cached in the `.cache/` directory to reduce API calls and improve performance on subsequent runs.

## Contributing

Feel free to open issues or submit pull requests for improvements or bug fixes.


### Complete Workflow with Bibliography

1. Create a `.env` file in the project root with your NCBI API key:

```
NCBI_API_KEY=your_api_key_here
```

To get an NCBI API key, visit: https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/

## Usage

### Basic Article Fetching

```python
from extend_pmid import Article

# Fetch Related Articles
article = Article("31875792")
print(article.pmid) # Access PMID
print(article.related) # Access related articles

# Fetch an Article with Bibliography
article_with_bib = Article("31875792", include_bib=True)
print(article_with_bib.bib) # Access bibliography info including title, authors, etc.
```

### Extending the Similar Article Network

```python
from extend_pmid import extend_pmid_set

# Start with a set of seed PMIDs
seed_pmids = {"31875792", "34735175"}

# Extend the Similar Article Network
extended_pmids = extend_pmid_set(
            pmid_set=seed_pmids,
            topk=10, # Number of related articles to consider per paper
            max_pmid=100, # Maximum total articles to collect
            max_retries=3 # Maximum retry attempts for failed requests
        )
```

```python
# Get extended article network with full bibliography information
articles = get_extended_articles(
            seed_pmids=seed_pmids,
            topk=10, # Number of related articles to consider per paper
            max_articles=100, # Maximum total articles to collect
            max_retries=3 # Maximum retry attempts for failed requests
        )
```
