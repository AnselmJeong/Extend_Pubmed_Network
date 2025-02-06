from metapub import PubMedFetcher, FindIt
from dotenv import load_dotenv
from tqdm import tqdm
from pathlib import Path
import requests
import random
from time import sleep
import os
from math import ceil

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
                print(f"Retrying bib fetch for {self.pmid} after {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
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


def _extend_pmid_set(pmid_set: set[str], topk: int = 10, min_pmid: int = 100, max_retries: int = 3) -> set[str]:
    """
    Extend a set of PMIDs by fetching related articles and adding them to the set.
    Args:
        pmid_set: Set of PMIDs to extend
        topk: Number of related articles per parent article to fetch
        min_pmid: Minimum number of PMIDs to be included in the return set
        max_retries: Maximum number of retries for fetching articles
    Returns:
        Set of extended PMIDs
    """

    topk = min(ceil(min_pmid * 1.5 / len(pmid_set)), topk)
    print(f"Fetching {topk} related articles per article")

    extended_articles = []

    for pmid in tqdm(pmid_set):
        for attempt in range(max_retries):
            try:
                article = Article(pmid, max_retries=max_retries)
                extended_articles.append(article)
                break
            except Exception as e:
                delay = _exponential_backoff(attempt)
                if attempt == max_retries - 1:
                    print(f"Failed to fetch article {pmid} after {max_retries} attempts: {str(e)}")
                else:
                    print(f"Retrying article {pmid} after {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    sleep(delay)

    # Get new PMIDs from extended articles
    new_pmid_set = pmid_set
    for article in extended_articles:
        new_pmid_set |= set(article.related["pubmed"][:topk])

    if len(new_pmid_set) < min_pmid and new_pmid_set:  # Check if we have any articles
        try:
            print(f"Found {len(new_pmid_set)} articles, extending further...")
            return _extend_pmid_set(new_pmid_set, topk, min_pmid, max_retries)
        except Exception as e:
            print(f"Stopping recursion due to error: {str(e)}")
            return new_pmid_set

    return new_pmid_set


def get_extended_articles(seed_pmids: list[str], topk: int = 10, min_articles: int = 50, max_retries: int = 3):
    """
    Get a list of related articles snow balling from a list of seed PMIDs.
    Args:
        seed_pmids: List of seed PMIDs
        topk: Number of related articles per parent article to fetch
        min_articles: Minimum number of articles to return
        max_retries: Maximum number of retries for fetching articles
    Returns:
        Dictionary with two keys:
            - "pmids": Set of extended PMIDs
            - "articles": List of extended articles
    """

    extended_pmid_set = _extend_pmid_set(set(seed_pmids), topk, min_articles, max_retries)
    # Return only the bibliography of the extended articles not related articles
    print(f"Fetching {len(extended_pmid_set)} articles")
    articles = []
    for pmid in tqdm(extended_pmid_set, desc="Fetching final set of articles"):
        try:
            article = Article(pmid, include_bib=True)
            articles.append(article)
        except Exception as e:
            print(f"Skipping article {pmid} due to error: {str(e)}")
            continue

    return {"pmids": extended_pmid_set, "articles": articles}


def get_highest_inbound_articles(extended_dict, topk=20):
    inbounds = {}
    for article in extended_dict["articles"]:
        # print(f"citedin: {extended_dict['pmids'] & set(article.related['citedin'])}")
        # print(f"refs: {extended_dict['pmids'] & set(article.related['refs'])}")
        inbound_count = len(extended_dict["pmids"] & set(article.related["citedin"])) + len(
            extended_dict["pmids"] & set(article.related["refs"])
        )
        inbounds[article.pmid] = inbound_count
    sorted_inbounds = dict(sorted(inbounds.items(), key=lambda item: item[1], reverse=True))

    top_inbounds = dict(list(sorted_inbounds.items())[:topk])

    return [article for article in extended_dict["articles"] if article.pmid in top_inbounds]


def _article_to_bibtex(article):
    bibformat = """@article{{{identifier},
        title = {{{title}}},
        author = {{{authors_str}}},
        year = {{{year}}},
        journal = {{{journal}}},
        doi = {{{doi}}},
    }}
    """
    return bibformat.format(
        identifier=article.bib.get("authors_str", " ").split(" ")[0] + article.bib.get("year"), **article.bib
    )


def articles_to_bibtex(articles):
    return "\n\n".join([_article_to_bibtex(article) for article in articles])


def download_articles(articles, save_path="./"):
    save_path = Path(save_path)
    for article in tqdm(articles, desc="Downloading articles"):
        src = FindIt(article.pmid)
        print(f"{article.pmid}: {src.url}")
        print(f"reason: {src.reason}")
        if src.url:
            try:
                response = requests.get(src.url)
                response.raise_for_status()
                file_path = save_path / f"{article.pmid}.pdf"
                with file_path.open("wb") as file:
                    file.write(response.content)
            except requests.exceptions.RequestException as e:
                print(f"Failed to download article {article.pmid} from {src.url}: {str(e)}")


if __name__ == "__main__":
    seed_pmids = ["31875792", "31875792"]
    articles = get_extended_articles(seed_pmids, topk=10, min_articles=100, max_retries=3)
    print(len(articles))
