#!/usr/bin/env python

import sys
import huggingface_hub as hf
from rich import print # pylint: disable=redefined-builtin

if __name__ == "__main__":
    sys.argv.pop(0)
    keyword = sys.argv[0] if len(sys.argv) > 0 else ''
    hf_api = hf.HfApi()
    model_filter = hf.ModelFilter(
        model_name=keyword,
        task='text-to-image',
        library=['diffusers'],
    )
    res = hf_api.list_models(filter=model_filter, full=True, limit=50, sort="downloads", direction=-1)
    models = [{ 'name': m.modelId, 'downloads': m.downloads, 'mtime': m.lastModified, 'url': f'https://huggingface.co/{m.modelId}', 'pipeline': m.pipeline_tag, 'tags': m.tags } for m in res]
    print(models)
