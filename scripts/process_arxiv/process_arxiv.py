from tqdm.auto import tqdm
import requests
from requests.adapters import HTTPAdapter, Retry
import datetime
import urllib.request
import time
import feedparser
import argparse

BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiYXJ4aXYtY2hhdGdwdC1wbHVnaW4ifQ.x4SINlGeCfjI1cXV31a4ZPvE9-bYz00bsIws64_VgSg"
headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}
s = requests.Session()
retries = Retry(
    total=5,  # number of retries before raising error
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504]
)
s.mount('http://', HTTPAdapter(max_retries=retries))


def retrieve(args, search_query):
    base_url = 'http://export.arxiv.org/api/query?';
    i = 0
    summaries = []
    urls = []
    total_papers = 0
    cur_year = int(datetime.datetime.now().year)

    while cur_year >= args.year:  # stop requesting when papers date reach 2018
        query = 'search_query={}&start={}&max_results={}&sortBy=submittedDate&sortOrder=descending'.format(
            search_query,
            i,
            args.batch_size
        )
        response = urllib.request.urlopen(base_url + query).read()
        feed = feedparser.parse(response)
        for entry in feed.entries:
            cur_year = int(entry.published[0:4])
            if cur_year < args.year:
                break
            else:
                summaries.append(entry.summary)
                urls.append(entry.id)
        total_papers += len(summaries)
        if len(summaries) != 0:
            vectors_to_be_upserted = []
            for idx, id in enumerate(urls):
                vectors_to_be_upserted.append(
                    {
                        'id': id,
                        'text': summaries[idx]
                    }
                )
            print(vectors_to_be_upserted)
            res = s.post(
                f"{args.endpoint_url}/upsert",
                headers=headers,
                json={
                    "documents": vectors_to_be_upserted
                }
            )
            print(res)
            print(res.content)
        i += len(summaries)
        ## TODO: Not sure if wait time is needed
        time.sleep(args.wait_time)
        summaries = []
        urls = []

        print(total_papers)
        break



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='noidea')
    parser.add_argument('--batch_size', required=False, type=int, default=100)
    parser.add_argument('--wait_time', required=False, type=float, default=0)
    parser.add_argument('--year', required=False, type=int, default=2023)
    parser.add_argument('--endpoint_url', required=False, type=str, default="http://0.0.0.0:8000")
    args = parser.parse_args()

    search_query = urllib.parse.quote("cat:cs.LG")
    retrieve(args, search_query)

    queries = [{'query': 'Learning Flow Functions from Data with Applications to Nonlinear Oscillators'}]
    res = requests.post(
        "http://0.0.0.0:8000/query",
        headers=headers,
        json={
            'queries': queries[:3]
        }
    )
    for query_result in res.json()['results']:
        query = query_result['query']
        answers = []
        scores = []
        for result in query_result['results']:
            answers.append(result['text'])
            scores.append(round(result['score'], 2))
        print("-" * 70 + "\n" + query + "\n\n" + "\n".join(
            [f"{s}: {a}" for a, s in zip(answers, scores)]) + "\n" + "-" * 70 + "\n\n")
