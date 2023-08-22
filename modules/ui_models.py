import os
import json
from datetime import datetime
import gradio as gr
from modules import sd_models, sd_vae, extras
from modules.ui_components import FormRow, ToolButton
from modules.ui_common import create_refresh_button
from modules.call_queue import wrap_gradio_gpu_call
from modules.shared import opts, log
import modules.errors


def create_ui():
    dummy_component = gr.Label(visible=False)

    with gr.Row(id="models_tab", elem_id="models_tab"):
        with gr.Column(elem_id='models_output_container', scale=1):
            # models_output = gr.Text(elem_id="models_output", value="", show_label=False)
            gr.HTML(elem_id="models_progress", value="")
            models_image = gr.Image(elem_id="models_image", show_label=False, interactive=False, type='pil')
            models_outcome = gr.HTML(elem_id="models_error", value="")

        with gr.Column(elem_id='models_input_container', scale=3):

            def gr_show(visible=True):
                return {"visible": visible, "__type__": "update"}

            with gr.Tab(label="Convert"):
                with gr.Row():
                    model_name = gr.Dropdown(sd_models.checkpoint_tiles(), label="Original model")
                    create_refresh_button(model_name, sd_models.list_models, lambda: {"choices": sd_models.checkpoint_tiles()}, "refresh_checkpoint_Z")
                with gr.Row():
                    custom_name = gr.Textbox(label="New model name")
                with gr.Row():
                    precision = gr.Radio(choices=["fp32", "fp16", "bf16"], value="fp16", label="Model precision")
                    m_type = gr.Radio(choices=["disabled", "no-ema", "ema-only"], value="disabled", label="Model pruning methods")
                with gr.Row():
                    checkpoint_formats = gr.CheckboxGroup(choices=["ckpt", "safetensors"], value=["safetensors"], label="Model Format")
                with gr.Row():
                    show_extra_options = gr.Checkbox(label="Show extra options", value=False)
                    fix_clip = gr.Checkbox(label="Fix clip", value=False)
                with gr.Row(visible=False) as extra_options:
                    specific_part_conv = ["copy", "convert", "delete"]
                    unet_conv = gr.Dropdown(specific_part_conv, value="convert", label="unet")
                    text_encoder_conv = gr.Dropdown(specific_part_conv, value="convert", label="text encoder")
                    vae_conv = gr.Dropdown(specific_part_conv, value="convert", label="vae")
                    others_conv = gr.Dropdown(specific_part_conv, value="convert", label="others")

                show_extra_options.change(fn=lambda x: gr_show(x), inputs=[show_extra_options], outputs=[extra_options])

                model_converter_convert = gr.Button(label="Convert", variant='primary')
                model_converter_convert.click(
                    fn=extras.run_modelconvert,
                    inputs=[
                        model_name,
                        checkpoint_formats,
                        precision, m_type, custom_name,
                        unet_conv,
                        text_encoder_conv,
                        vae_conv,
                        others_conv,
                        fix_clip
                    ],
                    outputs=[models_outcome]
                )

            with gr.Tab(label="Merge"):
                with gr.Row().style(equal_height=False):
                    with gr.Column(variant='compact'):
                        with FormRow():
                            custom_name = gr.Textbox(label="New model name")
                        with FormRow():
                            def sd_model_choices():
                                return ['None'] + sd_models.checkpoint_tiles()
                            primary_model_name = gr.Dropdown(sd_model_choices(), label="Primary model", value="None")
                            create_refresh_button(primary_model_name, sd_models.list_models, lambda: {"choices": sd_model_choices()}, "refresh_checkpoint_A")
                            secondary_model_name = gr.Dropdown(sd_model_choices(), label="Secondary model", value="None")
                            create_refresh_button(secondary_model_name, sd_models.list_models, lambda: {"choices": sd_model_choices()}, "refresh_checkpoint_B")
                            tertiary_model_name = gr.Dropdown(sd_model_choices(), label="Tertiary model", value="None")
                            create_refresh_button(tertiary_model_name, sd_models.list_models, lambda: {"choices": sd_model_choices()}, "refresh_checkpoint_C")
                        with FormRow():
                            interp_method = gr.Radio(choices=["No interpolation", "Weighted sum", "Add difference"], value="Weighted sum", label="Interpolation Method")
                            interp_amount = gr.Slider(minimum=0.0, maximum=1.0, step=0.05, label='Interpolation ratio from Primary to Secondary', value=0.5)
                        with FormRow():
                            checkpoint_format = gr.Radio(choices=["ckpt", "safetensors"], value="safetensors", label="Model format")
                        with gr.Box():
                            save_as_half = gr.Radio(choices=["fp16", "fp32"], value="fp16", label="Model precision", type="index")
                        with FormRow():
                            config_source = gr.Radio(choices=["Primary", "Secondary", "Tertiary", "None"], value="Primary", label="Model configuration", type="index")
                        with FormRow():
                            bake_in_vae = gr.Dropdown(choices=["None"] + list(sd_vae.vae_dict), value="None", label="Bake in VAE")
                            create_refresh_button(bake_in_vae, sd_vae.refresh_vae_list, lambda: {"choices": ["None"] + list(sd_vae.vae_dict)}, "modelmerger_refresh_bake_in_vae")
                        with FormRow():
                            discard_weights = gr.Textbox(value="", label="Discard weights with matching name")
                        with FormRow():
                            save_metadata = gr.Checkbox(value=True, label="Save metadata")
                        with gr.Row():
                            modelmerger_merge = gr.Button(value="Merge", variant='primary')

                def modelmerger(*args):
                    try:
                        results = extras.run_modelmerger(*args)
                    except Exception as e:
                        modules.errors.display(e, 'model merge')
                        sd_models.list_models()  # to remove the potentially missing models from the list
                        return [*[gr.Dropdown.update(choices=sd_models.checkpoint_tiles()) for _ in range(4)], f"Error merging checkpoints: {e}"]
                    return results

                modelmerger_merge.click(
                    fn=wrap_gradio_gpu_call(modelmerger, extra_outputs=lambda: [gr.update() for _ in range(4)]),
                    _js='modelmerger',
                    inputs=[
                        dummy_component,
                        primary_model_name,
                        secondary_model_name,
                        tertiary_model_name,
                        interp_method,
                        interp_amount,
                        save_as_half,
                        custom_name,
                        checkpoint_format,
                        config_source,
                        bake_in_vae,
                        discard_weights,
                        save_metadata,
                    ],
                    outputs=[
                        primary_model_name,
                        secondary_model_name,
                        tertiary_model_name,
                        dummy_component,
                        models_outcome,
                    ]
                )

            with gr.Tab(label="Validate"):
                model_headers = ['name', 'type', 'filename', 'hash', 'added', 'size', 'metadata']
                model_data = []

                with gr.Row():
                    model_list_btn = gr.Button(value="List model details", variant='primary')
                    model_checkhash_btn = gr.Button(value="Calculate hash for all models (may take a long time)", variant='primary')
                    model_checkhash_btn.click(fn=sd_models.update_model_hashes, inputs=[], outputs=[models_outcome])
                with gr.Row():
                    model_table = gr.DataFrame(
                        value = model_data,
                        headers = model_headers,
                        label = 'Model data',
                        show_label = True,
                        interactive = False,
                        wrap = True,
                        overflow_row_behaviour = 'paginate',
                        max_rows = 50,
                    )

                def list_models():
                    total_size = 0
                    model_data.clear()
                    txt = ''
                    for m in sd_models.checkpoints_list.values():
                        try:
                            stat = os.stat(m.filename)
                            m_name = m.name.replace('.ckpt', '').replace('.safetensors', '')
                            m_type = 'ckpt' if m.name.endswith('.ckpt') else 'safe'
                            m_meta = len(json.dumps(m.metadata)) - 2
                            m_size = round(stat.st_size / 1024 / 1024 / 1024, 3)
                            m_time = datetime.fromtimestamp(stat.st_mtime)
                            model_data.append([m_name, m_type, m.filename, m.hash, m_time, m_size, m_meta])
                            total_size += stat.st_size
                        except Exception as e:
                            txt += f"Error: {m.name} {e}<br>"
                        txt += f"Model list enumerated {len(sd_models.checkpoints_list.keys())} models in {round(total_size / 1024 / 1024 / 1024, 3)} GB<br>"
                    return model_data, txt

                model_list_btn.click(fn=list_models, inputs=[], outputs=[model_table, models_outcome])

            with gr.Tab(label="Huggingface"):
                data = []
                os.environ.setdefault('HF_HUB_DISABLE_EXPERIMENTAL_WARNING', '1')
                os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
                os.environ.setdefault('HF_HUB_DISABLE_IMPLICIT_TOKEN', '1')
                os.environ.setdefault('HUGGINGFACE_HUB_VERBOSITY', 'warning')

                def hf_search(keyword):
                    import huggingface_hub as hf
                    hf_api = hf.HfApi()
                    model_filter = hf.ModelFilter(
                        model_name=keyword,
                        task='text-to-image',
                        library=['diffusers'],
                    )
                    models = hf_api.list_models(filter=model_filter, full=True, limit=50, sort="downloads", direction=-1)
                    data.clear()
                    for model in models:
                        tags = [t for t in model.tags if not t.startswith('diffusers') and not t.startswith('license') and not t.startswith('arxiv') and len(t) > 2]
                        data.append([model.modelId, model.pipeline_tag, tags, model.downloads, model.lastModified, f'https://huggingface.co/{model.modelId}'])
                    return data

                def hf_select(evt: gr.SelectData, data):
                    return data[evt.index[0]][0]

                def hf_download_model(hub_id: str, token, variant, revision, mirror):
                    from modules.modelloader import download_diffusers_model
                    try:
                        download_diffusers_model(hub_id, cache_dir=opts.diffusers_dir, token=token, variant=variant, revision=revision, mirror=mirror)
                    except Exception as e:
                        log.error(f"Diffuser model downloaded error: model={hub_id} {e}")
                        return f"Diffuser model downloaded error: model={hub_id} {e}"
                    from modules.sd_models import list_models # pylint: disable=W0621
                    list_models()
                    log.info(f"Diffuser model downloaded: model={hub_id}")
                    return f'Diffuser model downloaded: model={hub_id}'

                with gr.Column(scale=6):
                    with gr.Row():
                        hf_search_text = gr.Textbox('', label = 'Seach models', placeholder='search huggingface models')
                        hf_search_btn = ToolButton(value="🔍", label="Search")
                    with gr.Row():
                        with gr.Column(scale=2):
                            with gr.Row():
                                hf_selected = gr.Textbox('', label = 'Select model', placeholder='select model from search results or enter model name manually')
                        with gr.Column(scale=1):
                            with gr.Row():
                                hf_variant = gr.Textbox(opts.cuda_dtype.lower(), label = 'Specify model variant', placeholder='')
                                hf_revision = gr.Textbox('', label = 'Specify model revision', placeholder='')
                    with gr.Row():
                        hf_token = gr.Textbox('', label = 'Huggingface token', placeholder='optional access token for private or gated models')
                        hf_mirror = gr.Textbox('', label = 'Huggingface mirror', placeholder='optional mirror site for downloads')
                with gr.Column(scale=1):
                    hf_download_model_btn = gr.Button(value="Download model", variant='primary')

                with gr.Row():
                    hf_headers = ['Name', 'Pipeline', 'Tags', 'Downloads', 'Updated', 'URL']
                    hf_types = ['str', 'str', 'str', 'number', 'date', 'markdown']
                    hf_results = gr.DataFrame([], label = 'Search results', show_label = True, interactive = False, wrap = True, overflow_row_behaviour = 'paginate', max_rows = 10, headers = hf_headers, datatype = hf_types, type='array')

                hf_search_text.submit(fn=hf_search, inputs=[hf_search_text], outputs=[hf_results])
                hf_search_btn.click(fn=hf_search, inputs=[hf_search_text], outputs=[hf_results])
                hf_results.select(fn=hf_select, inputs=[hf_results], outputs=[hf_selected])
                hf_download_model_btn.click(fn=hf_download_model, inputs=[hf_selected, hf_token, hf_variant, hf_revision, hf_mirror], outputs=[models_outcome])

            with gr.Tab(label="CivitAI"):
                data = []

                def civit_search(name, tag, model_type):
                    import requests
                    headers = { 'Content-type': 'application/json' }
                    url = 'https://civitai.com/api/v1/models?limit=25&types=Checkpoint&Sort=Newest'
                    if name is not None and len(name) > 0:
                        url += f'&query={name}'
                    if tag is not None and len(tag) > 0:
                        url += f'&tag={tag}'
                    r = requests.get(url, timeout=60, headers=headers)
                    log.debug(f'CivitAI search: name={name} tag={tag} status={r.status_code}')
                    if r.status_code != 200:
                        return [], [], []
                    body = r.json()
                    nonlocal data
                    data = body.get('items', [])
                    data1 = []
                    for model in data:
                        found = 0
                        for variant in model['modelVersions']:
                            if model_type == 'SD 1.5':
                                if 'SD 1.' in variant['baseModel']:
                                    found += 1
                            if model_type == 'SD XL':
                                if 'SDXL' in variant['baseModel']:
                                    found += 1
                            else:
                                if 'SD 1.' not in variant['baseModel'] and 'SDXL' not in variant['baseModel']:
                                    found += 1
                        if found > 0:
                            data1.append([
                                model['id'],
                                model['name'],
                                ', '.join(model['tags']),
                                model['stats']['downloadCount'],
                                model['stats']['rating']
                            ])
                    return data1, [], []

                def civit_select1(evt: gr.SelectData, in_data):
                    model_id = in_data[evt.index[0]][0]
                    data2 = []
                    preview_img = None
                    for model in data:
                        if model['id'] == model_id:
                            for d in model['modelVersions']:
                                if d.get('images') is not None and len(d['images']) > 0 and len(d['images'][0]['url']) > 0:
                                    preview_img = d['images'][0]['url']
                                data2.append([
                                    d['id'],
                                    d['modelId'],
                                    d['name'],
                                    d['baseModel'],
                                    d['createdAt'],
                                ])
                    log.debug(f'CivitAI select: model={in_data[evt.index[0]]} versions={len(data2)}')
                    return data2, preview_img

                def civit_select2(evt: gr.SelectData, in_data):
                    variant_id = in_data[evt.index[0]][0]
                    model_id = in_data[evt.index[0]][1]
                    data3 = []
                    for model in data:
                        if model['id'] == model_id:
                            for variant in model['modelVersions']:
                                if variant['id'] == variant_id:
                                    for f in variant['files']:
                                        data3.append([
                                            f['name'],
                                            round(f['sizeKB']),
                                            json.dumps(f['metadata']),
                                            f['downloadUrl'],
                                        ])
                    log.debug(f'CivitAI select: model={in_data[evt.index[0]]} files={len(data3)}')
                    return data3

                def civit_select3(evt: gr.SelectData, in_data):
                    log.debug(f'CivitAI select: variant={in_data[evt.index[0]]}')
                    return in_data[evt.index[0]][3], in_data[evt.index[0]][0], gr.update(interactive=True)

                def civit_download_model(model_url: str, model_name: str, model_path: str, image_url: str):
                    if model_url is None or len(model_url) == 0:
                        return 'No model selected'
                    try:
                        from modules.modelloader import download_civit_model
                        res = download_civit_model(model_url, model_name, model_path, image_url)
                    except Exception as e:
                        res = f"CivitAI model downloaded error: model={model_url} {e}"
                        log.error(res)
                        return res
                    from modules.sd_models import list_models # pylint: disable=W0621
                    list_models()
                    return res

                with gr.Row():
                    with gr.Column(scale=1):
                        civit_model_type = gr.Dropdown(label='Model type', choices=['SD 1.5', 'SD XL', 'Other'], value='SD 1.5')
                    with gr.Column(scale=15):
                        with gr.Row():
                            civit_search_text = gr.Textbox('', label = 'Seach models', placeholder='keyword')
                            civit_search_tag = gr.Textbox('', label = '', placeholder='tags')
                            civit_search_btn = ToolButton(value="🔍", label="Search", interactive=False)
                with gr.Row():
                    civit_download_model_btn = gr.Button(value="Download model", variant='primary')
                with gr.Row():
                    civit_name = gr.Textbox('', label = 'Model name', placeholder='select model from search results', visible=True)
                    civit_selected = gr.Textbox('', label = 'Model URL', placeholder='select model from search results', visible=True)
                    civit_path = gr.Textbox('', label = 'Download path', placeholder='optional subfolder path where to save model', visible=True)
                with gr.Row():
                    with gr.Column():
                        civit_headers2 = ['ID', 'ModelID', 'Name', 'Base', 'Created', 'Preview']
                        civit_types2 = ['number', 'number', 'str', 'str', 'date', 'str']
                        civit_results2 = gr.DataFrame([], label = 'Model versions', show_label = True, interactive = False, wrap = True, overflow_row_behaviour = 'paginate', max_rows = 10, headers = civit_headers2, datatype = civit_types2, type='array')
                    with gr.Column():
                        civit_headers3 = ['Name', 'Size', 'Metadata', 'URL']
                        civit_types3 = ['str', 'number', 'str', 'str']
                        civit_results3 = gr.DataFrame([], label = 'Model variants', show_label = True, interactive = False, wrap = True, overflow_row_behaviour = 'paginate', max_rows = 10, headers = civit_headers3, datatype = civit_types3, type='array')
                with gr.Row():
                    civit_headers1 = ['ID', 'Name', 'Tags', 'Downloads', 'Rating']
                    civit_types1 = ['number', 'str', 'str', 'number', 'number']
                    civit_results1 = gr.DataFrame([], label = 'Search results', show_label = True, interactive = False, wrap = True, overflow_row_behaviour = 'paginate', max_rows = 10, headers = civit_headers1, datatype = civit_types1, type='array')

                civit_search_text.submit(fn=civit_search, inputs=[civit_search_text, civit_search_tag, civit_model_type], outputs=[civit_results1, civit_results2, civit_results3])
                civit_search_tag.submit(fn=civit_search, inputs=[civit_search_text, civit_search_tag, civit_model_type], outputs=[civit_results1, civit_results2, civit_results3])
                civit_search_btn.click(fn=civit_search, inputs=[civit_search_text, civit_search_tag, civit_model_type], outputs=[civit_results1, civit_results2, civit_results3])
                civit_results1.select(fn=civit_select1, inputs=[civit_results1], outputs=[civit_results2, models_image])
                civit_results2.select(fn=civit_select2, inputs=[civit_results2], outputs=[civit_results3])
                civit_results3.select(fn=civit_select3, inputs=[civit_results3], outputs=[civit_selected, civit_name, civit_search_btn])
                civit_download_model_btn.click(fn=civit_download_model, inputs=[civit_selected, civit_name, civit_path, models_image], outputs=[models_outcome])
