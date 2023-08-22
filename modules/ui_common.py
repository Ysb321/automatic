import json
import html
import os
import shutil
import platform
import subprocess
import gradio as gr
from modules import call_queue, shared
from modules.generation_parameters_copypaste import image_from_url_text
import modules.images


folder_symbol = '\U0001f4c2'  # 📂


def update_generation_info(generation_info, html_info, img_index):
    try:
        generation_info = json.loads(generation_info)
        if img_index < 0 or img_index >= len(generation_info["infotexts"]):
            return html_info, generation_info
        infotext = generation_info["infotexts"][img_index]
        html_info_formatted = infotext_to_html(infotext)
        return html_info, html_info_formatted
    except Exception:
        pass
    return html_info, html_info


def plaintext_to_html(text):
    res = '<p class="plaintext">' + "<br>\n".join([f"{html.escape(x)}" for x in text.split('\n')]) + '</p>'
    return res


def infotext_to_html(text):
    res = '<p class="html_info">Prompt: ' + html.escape(text or '').replace('\n', '<br>') + '</p>'
    sections = res.split('Steps:') # before and after prompt+negprompt'
    if len(sections) > 1:
        res = sections[0] + '<br>Steps: ' + sections[1].strip().replace(', ', ' | ')
    res = res.replace('<br><br>', '<br>')
    return res


def delete_files(js_data, images, _html_info, index):
    try:
        data = json.loads(js_data)
    except Exception:
        data = { 'index_of_first_image': 0 }
    start_index = 0
    if index > -1 and shared.opts.save_selected_only and (index >= data['index_of_first_image']):
        images = [images[index]]
        start_index = index
        filenames = []
    filenames = []
    fullfns = []
    for _image_index, filedata in enumerate(images, start_index):
        if 'name' in filedata and os.path.isfile(filedata['name']):
            fullfn = filedata['name']
            filenames.append(os.path.basename(fullfn))
            try:
                os.remove(fullfn)
                base, _ext = os.path.splitext(fullfn)
                desc = f'{base}.txt'
                if os.path.exists(desc):
                    os.remove(desc)
                fullfns.append(fullfn)
                shared.log.info(f"Deleting image: {fullfn}")
            except Exception as e:
                shared.log.error(f'Error deleting file: {fullfn} {e}')
    images = [image for image in images if image['name'] not in fullfns]
    return images, plaintext_to_html(f"Deleted: {filenames[0] if len(filenames) > 0 else 'none'}")


def save_files(js_data, images, html_info, index):
    os.makedirs(shared.opts.outdir_save, exist_ok=True)

    class PObject: # pylint: disable=too-few-public-methods
        def __init__(self, d=None):
            if d is not None:
                for key, value in d.items():
                    setattr(self, key, value)
            self.seed = getattr(self, 'seed', None) or getattr(self, 'Seed', None)
            self.prompt = getattr(self, 'prompt', None) or getattr(self, 'Prompt', None)
            self.all_seeds = getattr(self, 'all_seeds', [self.seed])
            self.all_prompts = getattr(self, 'all_prompts', [self.prompt])
            self.infotext = html_info
            self.infotexts = getattr(self, 'infotexts', [html_info])
            self.index_of_first_image = getattr(self, 'index_of_first_image', 0)
    try:
        data = json.loads(js_data)
    except Exception:
        data = {}
    p = PObject(data)
    start_index = 0
    if index > -1 and shared.opts.save_selected_only and (index >= p.index_of_first_image):  # ensures we are looking at a specific non-grid picture, and we have save_selected_only # pylint: disable=no-member
        images = [images[index]]
        start_index = index
    filenames = []
    fullfns = []
    for image_index, filedata in enumerate(images, start_index):
        is_grid = image_index < p.index_of_first_image # pylint: disable=no-member
        i = 0 if is_grid else (image_index - p.index_of_first_image) # pylint: disable=no-member
        while len(p.all_seeds) <= i:
            p.all_seeds.append(p.seed)
        while len(p.all_prompts) <= i:
            p.all_prompts.append(p.prompt)
        while len(p.infotexts) <= i + 1:
            p.infotexts.append(p.infotext)
        if 'name' in filedata and ('tmp' not in filedata['name']) and os.path.isfile(filedata['name']):
            fullfn = filedata['name']
            filenames.append(os.path.basename(fullfn))
            fullfns.append(fullfn)
            destination = shared.opts.outdir_save
            if shared.opts.use_save_to_dirs_for_ui:
                namegen = modules.images.FilenameGenerator(p, seed=p.all_seeds[i], prompt=p.all_prompts[i], image=None)  # pylint: disable=no-member
                dirname = namegen.apply(shared.opts.directories_filename_pattern or "[prompt_words]").lstrip(' ').rstrip('\\ /')
                destination = os.path.join(destination, dirname)
                os.makedirs(destination, exist_ok = True)
            shutil.copy(fullfn, destination)
            shared.log.info(f"Copying image: {fullfn} -> {destination}")
        else:
            image = image_from_url_text(filedata)
            # infotext is offset by 1 because the first image is the grid
            fullfn, txt_fullfn = modules.images.save_image(image, shared.opts.outdir_save, "", seed=p.all_seeds[i], prompt=p.all_prompts[i], info=p.infotexts[i + 1], extension=shared.opts.samples_format, grid=is_grid, p=p, save_to_dirs=shared.opts.use_save_to_dirs_for_ui)
            if fullfn is None:
                continue
            filename = os.path.relpath(fullfn, shared.opts.outdir_save)
            filenames.append(filename)
            fullfns.append(fullfn)
            if txt_fullfn:
                filenames.append(os.path.basename(txt_fullfn))
                fullfns.append(txt_fullfn)
    if shared.opts.samples_save_zip and len(fullfns) > 1:
        zip_filepath = os.path.join(shared.opts.outdir_save, "images.zip")
        from zipfile import ZipFile
        with ZipFile(zip_filepath, "w") as zip_file:
            for i in range(len(fullfns)):
                with open(fullfns[i], mode="rb") as f:
                    zip_file.writestr(filenames[i], f.read())
        fullfns.insert(0, zip_filepath)
    return gr.File.update(value=fullfns, visible=True), plaintext_to_html(f"Saved: {filenames[0] if len(filenames) > 0 else 'none'}")


def create_output_panel(tabname, outdir):
    import modules.generation_parameters_copypaste as parameters_copypaste

    def open_folder(f):
        if not os.path.exists(f):
            shared.log.warning(f'Folder "{f}" does not exist. After you create an image, the folder will be created.')
            return
        elif not os.path.isdir(f):
            shared.log.warning(f"An open_folder request was made with an argument that is not a folder: {f}")
            return

        if not shared.cmd_opts.hide_ui_dir_config:
            path = os.path.normpath(f)
            if platform.system() == "Windows":
                os.startfile(path) # pylint: disable=no-member
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path]) # pylint: disable=consider-using-with
            elif "microsoft-standard-WSL2" in platform.uname().release:
                subprocess.Popen(["wsl-open", path]) # pylint: disable=consider-using-with
            else:
                subprocess.Popen(["xdg-open", path]) # pylint: disable=consider-using-with

    with gr.Column(variant='panel', elem_id=f"{tabname}_results"):
        with gr.Group(elem_id=f"{tabname}_gallery_container"):
            result_gallery = gr.Gallery(value=[], label='Output', show_label=False, elem_id=f"{tabname}_gallery", elem_classes="logo").style(preview=False, container=False, columns=[1,2,3,4,5,6]) # <576px, <768px, <992px, <1200px, <1400px, >1400px

        with gr.Column(elem_id=f"{tabname}_footer", elem_classes="gallery_footer"):
            with gr.Row(elem_id=f"image_buttons_{tabname}", elem_classes="image-buttons"):
                if not shared.cmd_opts.listen:
                    open_folder_button = gr.Button('Show', visible=not shared.cmd_opts.hide_ui_dir_config, elem_id=f'open_folder_{tabname}')
                    open_folder_button.click(fn=lambda: open_folder(shared.opts.outdir_samples or outdir), inputs=[], outputs=[])
                else:
                    clip_files = gr.Button('Copy', elem_id=f'open_folder_{tabname}')
                    clip_files.click(fn=None, _js='clip_gallery_urls', inputs=[result_gallery], outputs=[])
                save = gr.Button('Save', elem_id=f'save_{tabname}')
                delete = gr.Button('Delete', elem_id=f'delete_{tabname}')
                buttons = parameters_copypaste.create_buttons(["img2img", "inpaint", "extras"])

            download_files = gr.File(None, file_count="multiple", interactive=False, show_label=False, visible=False, elem_id=f'download_files_{tabname}')
            with gr.Group():
                html_info = gr.HTML(elem_id=f'html_info_{tabname}', elem_classes="infotext", visible=False) # contains raw infotext as returned by wrapped call
                html_info_formatted = gr.HTML(elem_id=f'html_info_formatted_{tabname}', elem_classes="infotext", visible=True) # contains html formatted infotext
                html_info.change(fn=infotext_to_html, inputs=[html_info], outputs=[html_info_formatted], show_progress=False)
                html_log = gr.HTML(elem_id=f'html_log_{tabname}')
                generation_info = gr.Textbox(visible=False, elem_id=f'generation_info_{tabname}')
                generation_info_button = gr.Button(visible=False, elem_id=f"{tabname}_generation_info_button")

                generation_info_button.click(fn=update_generation_info, _js="(x, y, z) => [x, y, selected_gallery_index()]", show_progress=False, # triggered on gallery change from js
                    inputs=[generation_info, html_info, html_info],
                    outputs=[html_info, html_info_formatted],
                )
                save.click(fn=call_queue.wrap_gradio_call(save_files), _js="(x, y, z, i) => [x, y, z, selected_gallery_index()]", show_progress=False,
                    inputs=[generation_info, result_gallery, html_info, html_info],
                    outputs=[download_files, html_log],
                )
                delete.click(fn=call_queue.wrap_gradio_call(delete_files), _js="(x, y, z, i) => [x, y, z, selected_gallery_index()]",
                    inputs=[generation_info, result_gallery, html_info, html_info],
                    outputs=[result_gallery, html_log],
                )

            if tabname == "txt2img":
                paste_field_names = modules.scripts.scripts_txt2img.paste_field_names
            elif tabname == "img2img":
                paste_field_names = modules.scripts.scripts_img2img.paste_field_names
            else:
                paste_field_names = []
            for paste_tabname, paste_button in buttons.items():
                parameters_copypaste.register_paste_params_button(parameters_copypaste.ParamBinding(
                    paste_button=paste_button, tabname=paste_tabname, source_tabname=("txt2img" if tabname == "txt2img" else None), source_image_component=result_gallery, paste_field_names=paste_field_names
                ))
            return result_gallery, generation_info, html_info, html_info_formatted, html_log


def create_refresh_button(refresh_component, refresh_method, refreshed_args, elem_id):

    def refresh():
        refresh_method()
        args = refreshed_args() if callable(refreshed_args) else refreshed_args
        for k, v in args.items():
            setattr(refresh_component, k, v)
        return gr.update(**(args or {}))

    from modules.ui_components import ToolButton
    refresh_symbol = '\U0001f504'  # 🔄
    refresh_button = ToolButton(value=refresh_symbol, elem_id=elem_id)
    refresh_button.click(fn=refresh, inputs=[], outputs=[refresh_component])
    return refresh_button
