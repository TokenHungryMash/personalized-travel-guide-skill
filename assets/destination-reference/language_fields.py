"""Normalize unused English-only translation fields without changing authored files."""
from copy import deepcopy

def normalized_language_content(editorial, language):
    if str(language).lower().split('-')[0] != 'en' or not isinstance(editorial,dict):
        return editorial
    result=deepcopy(editorial)
    def remove_empty(item,keys):
        if isinstance(item,dict):
            for key in keys:
                if isinstance(item.get(key),str) and not item[key].strip():item.pop(key)
    for collection in ('phrases','words'):
        groups=result.get(collection,{})
        if not isinstance(groups,dict):continue
        for rows in groups.values():
            if not isinstance(rows,list):continue
            for row in rows:
                if not isinstance(row,dict):continue
                remove_empty(row,('english',))
                field=row.get('input',{})
                remove_empty(field,('englishLabel','englishPlaceholder'))
                if isinstance(field,dict) and isinstance(field.get('options'),list):
                    for option in field['options']:remove_empty(option,('english',))
    return result
