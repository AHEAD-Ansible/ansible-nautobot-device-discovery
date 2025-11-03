def _extract_chunks(result_obj, fact_key):
    chunks = []
    if not result_obj:
        return chunks

    if isinstance(result_obj, dict):
        # Standard ansible_facts or top-level var
        if "ansible_facts" in result_obj and fact_key in result_obj["ansible_facts"]:
            chunks.extend(result_obj["ansible_facts"][fact_key])
        elif fact_key in result_obj:
            chunks.extend(result_obj[fact_key])
        # Recurse into register/include results
        elif "results" in result_obj and isinstance(result_obj["results"], list):
            for res in result_obj["results"]:
                chunks.extend(_extract_chunks(res, fact_key))
        return chunks

    if isinstance(result_obj, list):
        for res in result_obj:
            chunks.extend(_extract_chunks(res, fact_key))
    return chunks


def merge_upsert_results(existing=None, create_results=None, update_results=None):
    """Merge existing, create, and update chunks into one unified list."""
    existing_list = existing or []
    created = _extract_chunks(create_results, "created_chunk")
    updated = _extract_chunks(update_results, "updated_chunk")

    # Merge and deduplicate by ID when present
    merged = {str(obj.get("id", f"tmp-{i}")): obj for i, obj in enumerate(existing_list + created + updated)}
    return list(merged.values())


class FilterModule(object):
    def filters(self):
        return {"merge_upsert_results": merge_upsert_results}
