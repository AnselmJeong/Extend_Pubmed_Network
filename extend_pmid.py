from metapub import PubMedFetcher
from dotenv import load_dotenv
import tqdm
import random
from time import sleep
import os

load_dotenv()

fetcher = PubMedFetcher(cachedir="./.cache/", api_key=os.getenv("NCBI_API_KEY"))


def _exponential_backoff(attempt, base_delay=1, max_delay=60):
    """Calculate delay with jitter for exponential backoff"""
    delay = min(base_delay * (2**attempt), max_delay)
    jitter = random.uniform(0, 0.1 * delay)  # 10% jitter
    return delay + jitter


class Article:
    def __init__(self, pmid: str | int, include_bib: bool = False, max_retries: int = 3):
        if isinstance(pmid, int):
            pmid = str(pmid)
        self.pmid = pmid

        if include_bib:
            self._fetch_bib(max_retries)
        self._fetch_related(max_retries)

    def _fetch_bib(self, max_retries):
        for attempt in range(max_retries):
            try:
                article = fetcher.article_by_pmid(self.pmid)
                self.bib = {
                    key: getattr(article, key)
                    for key in [
                        "authors_str",
                        "title",
                        "doi",
                        "year",
                        "journal",
                        "keywords",
                        "abstract",
                    ]
                }
                return
            except Exception as e:
                delay = _exponential_backoff(attempt)
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to fetch bibliography for {self.pmid}: {str(e)}")
                print(
                    f"Retrying bib fetch for {self.pmid} after {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                sleep(delay)

    def _fetch_related(self, max_retries):
        for attempt in range(max_retries):
            try:
                related = fetcher.related_pmids(self.pmid)
                self.related = {key: related.get(key, []) for key in ["pubmed", "citedin", "refs"]}
                return
            except Exception as e:
                delay = _exponential_backoff(attempt)
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to fetch related articles for {self.pmid}: {str(e)}")
                print(
                    f"Retrying related fetch for {self.pmid} after {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                sleep(delay)


def extend_pmid_set(
    pmid_set: set[str], topk: int = 10, max_pmid: int = 100, max_retries: int = 3
) -> set[str]:
    extended_articles = []

    for pmid in tqdm.tqdm(pmid_set):
        for attempt in range(max_retries):
            try:
                article = Article(pmid, max_retries=max_retries)
                sleep(1)  # Basic rate limiting
                extended_articles.append(article)
                break
            except Exception as e:
                delay = _exponential_backoff(attempt)
                if attempt == max_retries - 1:
                    print(f"Failed to fetch article {pmid} after {max_retries} attempts: {str(e)}")
                else:
                    print(
                        f"Retrying article {pmid} after {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    sleep(delay)

    # Get new PMIDs from extended articles
    new_pmid_set = set()
    for article in extended_articles:
        new_pmid_set |= set(article.related["pubmed"][:topk])

    if len(new_pmid_set) < max_pmid and new_pmid_set:  # Check if we have any articles
        try:
            print(f"Found {len(new_pmid_set)} articles, extending further...")
            return extend_pmid_set(new_pmid_set, topk, max_pmid, max_retries)
        except Exception as e:
            print(f"Stopping recursion due to error: {str(e)}")
            return new_pmid_set

    return new_pmid_set

def get_extended_articles(seed_pmids: list[str], topk: int = 10, max_articles: int = 100, max_retries: int = 3):
    extended_pmid_set = extend_pmid_set(set(seed_pmids), topk, max_articles, max_retries)
    articles = [Article(pmid, include_bib=True) for pmid in extended_pmid_set]
    return articles


if __name__ == "__main__":
    seed_pmids = ["31875792", "31875792"]
    articles = get_extended_articles(seed_pmids, topk=10, max_articles=100, max_retries=3)
    print(len(articles))
