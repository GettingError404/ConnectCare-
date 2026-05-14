from typing import Optional


def paginate(query, page: int = 1, per_page: int = 25):
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 25
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page)
