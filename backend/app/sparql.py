import os
import requests

FUSEKI_USER = os.getenv("FUSEKI_USER", "admin")
FUSEKI_PASSWORD = os.getenv("FUSEKI_PASSWORD", "admin")


def _auth():
    return (FUSEKI_USER, FUSEKI_PASSWORD)


def query_select(query: str, query_url: str):
    r = requests.post(
        query_url,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        auth=_auth(),
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()

    vars_ = data.get("head", {}).get("vars", [])
    rows = []

    for binding in data.get("results", {}).get("bindings", []):
        row = {}
        for v in vars_:
            if v in binding:
                row[v] = binding[v].get("value")
        rows.append(row)

    return rows


def query_construct(query: str, query_url: str):
    r = requests.post(
        query_url,
        data={"query": query},
        headers={"Accept": "text/turtle"},
        auth=_auth(),
        timeout=20,
    )
    r.raise_for_status()
    return r.text


def fuseki_update_insert(graph, update_url: str):
    triples = []

    for s, p, o in graph:
        triples.append(f"{s.n3()} {p.n3()} {o.n3()} .")

    if not triples:
        return

    update = "INSERT DATA { " + "\n".join(triples) + " }"

    r = requests.post(
        update_url,
        data={"update": update},
        auth=_auth(),
        timeout=20,
    )
    r.raise_for_status()
