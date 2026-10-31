"""Print the field names of a few GraphQL types, to find where Rivian moved the fields the poller
needs (e.g. consumerStatuses was rejected from the order query). Names only, no values, so the
workflow log is safe to leave public.

    python -m app.probe Order ConsumerVehicleStatuses PurchaseProcessSteps
"""

from __future__ import annotations

import sys

from . import crypto, state
from .rivian import RivianClient, RivianError
from .rivian import queries as Q
from .rivian.client import Session

DEFAULT_TYPES = ["Order", "ConsumerVehicleStatuses", "PurchaseProcessSteps", "T2DServiceStatus", "Query"]


def type_query(name: str) -> dict:
    return {
        "operationName": "probe",
        "query": 'query probe { __type(name: "%s") { name fields { name type { name kind ofType { name kind } } } } }' % name,
        "variables": {},
    }


def main(names: list[str]) -> int:
    sess = crypto.read_enc(state.SESSION_ENC)
    if not sess:
        print("no session; run the Login workflow first")
        return 1
    client = RivianClient(Session.from_dict(sess))
    for url_name, url in (("orders", Q.ORDERS), ("gateway", Q.GATEWAY)):
        for name in names or DEFAULT_TYPES:
            try:
                data = client._post(url, type_query(name), client._headers(t2d=True))
            except RivianError as e:
                print(f"[{url_name}] {name}: {str(e)[:120]}")
                continue
            t = data.get("__type")
            if not t:
                print(f"[{url_name}] {name}: not found")
                continue
            fields = ", ".join(f["name"] for f in t.get("fields") or [])
            print(f"[{url_name}] {name}: {fields}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
