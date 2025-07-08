from qdrant_playground import init_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue, PayloadSchemaType
import numpy as np
import pprint


client = init_qdrant_client()

def search_qdrant_without_filter():

    query_vec = np.random.uniform(low=0.0, high=1.0, size=71).tolist()
    search_without_filter = client.search(
        collection_name="tracks",
        query_vector=query_vec,
        with_payload=True,
        with_vectors=True,
        limit=1
    )
    # print("search without filter")
    # pprint.pprint(search_without_filter)

    return search_without_filter

def search_qdrant_with_filter():

    query_vec = np.random.uniform(low=0.0, high=1.0, size=71).tolist()
    client.create_payload_index(
        collection_name="tracks",
        field_name="releasecountry",
        field_schema=PayloadSchemaType.KEYWORD
    )

    search_with_filter = client.search(
        collection_name="tracks",
        query_vector=query_vec,
        query_filter=Filter(
            must=[FieldCondition(key="releasecountry", match=MatchValue(value="US"))]
        ),
        with_payload=True,
        # with_vectors=True, # prints the query vector of the song
        limit=5,
    )
    # print("search with filter")
    # pprint.pprint(search_with_filter)

    return search_with_filter

def main():
    search_qdrant_with_filter()
    search_qdrant_without_filter()

if __name__ == "__main__":
    main()