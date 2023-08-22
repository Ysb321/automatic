import os
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageChops, UnidentifiedImageError
import modules.scripts
from modules import sd_samplers, shared, processing, images
from modules.generation_parameters_copypaste import create_override_settings_dict
from modules.ui import plaintext_to_html
from modules.memstats import memory_stats


def process_batch(p, input_files, input_dir, output_dir, inpaint_mask_dir, args):
    shared.log.debug(f'batch: {input_dir}|{output_dir}|{inpaint_mask_dir}')
    processing.fix_seed(p)
    if input_files is not None and len(input_files) > 0:
        image_files = [f.name for f in input_files]
    else:
        if not os.path.isdir(input_dir):
            shared.log.error(f"Input directory not found: {input_dir}")
            return
        image_files = shared.listfiles(input_dir)
    is_inpaint_batch = False
    if inpaint_mask_dir:
        inpaint_masks = shared.listfiles(inpaint_mask_dir)
        is_inpaint_batch = len(inpaint_masks) > 0
    if is_inpaint_batch:
        shared.log.info(f"\nInpaint batch is enabled. {len(inpaint_masks)} masks found.")
    shared.log.info(f"Will process {len(image_files)} images, creating {p.n_iter * p.batch_size} new images for each.")
    save_normally = output_dir == ''
    p.do_not_save_grid = True
    p.do_not_save_samples = not save_normally
    shared.state.job_count = len(image_files) * p.n_iter
    for i, image_file in enumerate(image_files):
        shared.state.job = f"{i+1} out of {len(image_files)}"
        if shared.state.skipped:
            shared.state.skipped = False
        if shared.state.interrupted:
            break
        try:
            img = Image.open(image_file)
        except UnidentifiedImageError as e:
            shared.log.error(f"Image error: {e}")
            continue
        img = ImageOps.exif_transpose(img)
        p.init_images = [img] * p.batch_size

        if is_inpaint_batch:
            # try to find corresponding mask for an image using simple filename matching
            mask_image_path = os.path.join(inpaint_mask_dir, os.path.basename(image_file))
            # if not found use first one ("same mask for all images" use-case)
            if mask_image_path not in inpaint_masks:
                mask_image_path = inpaint_masks[0]
            mask_image = Image.open(mask_image_path)
            p.image_mask = mask_image

        proc = modules.scripts.scripts_img2img.run(p, *args)
        if proc is None:
            proc = processing.process_images(p)
        for n, image in enumerate(proc.images):
            basename, ext = os.path.splitext(os.path.basename(image_file))
            ext = ext[1:]
            if len(proc.images) > 1:
                basename = f'{basename}-{n}'
            if not shared.opts.use_original_name_batch:
                basename = ''
                ext = shared.opts.samples_format
            if output_dir == '':
                output_dir = shared.opts.outdir_img2img_samples
            if not save_normally:
                os.makedirs(output_dir, exist_ok=True)
            geninfo, items = images.read_info_from_image(image)
            for k, v in items.items():
                image.info[k] = v
            images.save_image(image, path=output_dir, basename=basename, seed=None, prompt=None, extension=ext, info=geninfo, short_filename=True, no_prompt=True, grid=False, pnginfo_section_name="extras", existing_info=image.info, forced_filename=None)
        shared.log.debug(f'Processed: {len(image_files)} Memory: {memory_stats()} batch')


def img2img(id_task: str, mode: int, prompt: str, negative_prompt: str, prompt_styles, init_img, sketch, init_img_with_mask, inpaint_color_sketch, inpaint_color_sketch_orig, init_img_inpaint, init_mask_inpaint, steps: int, sampler_index: int, latent_index: int, mask_blur: int, mask_alpha: float, inpainting_fill: int, full_quality: bool, restore_faces: bool, tiling: bool, n_iter: int, batch_size: int, cfg_scale: float, image_cfg_scale: float, diffusers_guidance_rescale: float, refiner_start: float, clip_skip: int, denoising_strength: float, seed: int, subseed: int, subseed_strength: float, seed_resize_from_h: int, seed_resize_from_w: int, selected_scale_tab: int, height: int, width: int, scale_by: float, resize_mode: int, inpaint_full_res: bool, inpaint_full_res_padding: int, inpainting_mask_invert: int, img2img_batch_files: list, img2img_batch_input_dir: str, img2img_batch_output_dir: str, img2img_batch_inpaint_mask_dir: str, override_settings_texts, *args): # pylint: disable=unused-argument

    if shared.sd_model is None:
        shared.log.warning('Model not loaded')
        return [], '', '', 'Error: model not loaded'

    shared.log.debug(f'img2img: id_task={id_task}|mode={mode}|prompt={prompt}|negative_prompt={negative_prompt}|prompt_styles={prompt_styles}|init_img={init_img}|sketch={sketch}|init_img_with_mask={init_img_with_mask}|inpaint_color_sketch={inpaint_color_sketch}|inpaint_color_sketch_orig={inpaint_color_sketch_orig}|init_img_inpaint={init_img_inpaint}|init_mask_inpaint={init_mask_inpaint}|steps={steps}|sampler_index={sampler_index}|latent_index={latent_index}|mask_blur={mask_blur}|mask_alpha={mask_alpha}|inpainting_fill={inpainting_fill}|full_quality={full_quality}|restore_faces={restore_faces}|tiling={tiling}|n_iter={n_iter}|batch_size={batch_size}|cfg_scale={cfg_scale}|image_cfg_scale={image_cfg_scale}|clip_skip={clip_skip}|denoising_strength={denoising_strength}|seed={seed}|subseed{subseed}|subseed_strength={subseed_strength}|seed_resize_from_h={seed_resize_from_h}|seed_resize_from_w={seed_resize_from_w}|selected_scale_tab={selected_scale_tab}|height={height}|width={width}|scale_by={scale_by}|resize_mode={resize_mode}|inpaint_full_res={inpaint_full_res}|inpaint_full_res_padding={inpaint_full_res_padding}|inpainting_mask_invert={inpainting_mask_invert}|img2img_batch_files={img2img_batch_files}|img2img_batch_input_dir={img2img_batch_input_dir}|img2img_batch_output_dir={img2img_batch_output_dir}|img2img_batch_inpaint_mask_dir={img2img_batch_inpaint_mask_dir}|override_settings_texts={override_settings_texts}|args={args}')

    if init_img is None:
        shared.log.debug('Init image not set')

    if sampler_index is None:
        sampler_index = 0
    if latent_index is None:
        latent_index = 0

    override_settings = create_override_settings_dict(override_settings_texts)

    is_batch = mode == 5
    if mode == 0:  # img2img
        if init_img is None:
            return
        image = init_img.convert("RGB")
        mask = None
    elif mode == 1:  # img2img sketch
        if sketch is None:
            return
        image = sketch.convert("RGB")
        mask = None
    elif mode == 2:  # inpaint
        if init_img_with_mask is None:
            return
        image = init_img_with_mask["image"]
        mask = init_img_with_mask["mask"]
        alpha_mask = ImageOps.invert(image.split()[-1]).convert('L').point(lambda x: 255 if x > 0 else 0, mode='1')
        mask = ImageChops.lighter(alpha_mask, mask.convert('L')).convert('L')
        image = image.convert("RGB")
    elif mode == 3:  # inpaint sketch
        if inpaint_color_sketch is None:
            return
        image = inpaint_color_sketch
        orig = inpaint_color_sketch_orig or inpaint_color_sketch
        pred = np.any(np.array(image) != np.array(orig), axis=-1)
        mask = Image.fromarray(pred.astype(np.uint8) * 255, "L")
        mask = ImageEnhance.Brightness(mask).enhance(1 - mask_alpha / 100)
        blur = ImageFilter.GaussianBlur(mask_blur)
        image = Image.composite(image.filter(blur), orig, mask.filter(blur))
        image = image.convert("RGB")
    elif mode == 4:  # inpaint upload mask
        if init_img_inpaint is None:
            return
        image = init_img_inpaint
        mask = init_mask_inpaint
    else:
        image = None
        mask = None
    if image is not None:
        image = ImageOps.exif_transpose(image)
        if selected_scale_tab == 1 and resize_mode != 0:
            width = int(image.width * scale_by)
            height = int(image.height * scale_by)

    p = processing.StableDiffusionProcessingImg2Img(
        sd_model=shared.sd_model,
        outpath_samples=shared.opts.outdir_samples or shared.opts.outdir_img2img_samples,
        outpath_grids=shared.opts.outdir_grids or shared.opts.outdir_img2img_grids,
        prompt=prompt,
        negative_prompt=negative_prompt,
        styles=prompt_styles,
        seed=seed,
        subseed=subseed,
        subseed_strength=subseed_strength,
        seed_resize_from_h=seed_resize_from_h,
        seed_resize_from_w=seed_resize_from_w,
        seed_enable_extras=True,
        sampler_name=sd_samplers.samplers_for_img2img[sampler_index].name,
        latent_sampler=sd_samplers.samplers[latent_index].name,
        batch_size=batch_size,
        n_iter=n_iter,
        steps=steps,
        cfg_scale=cfg_scale,
        clip_skip=clip_skip,
        width=width,
        height=height,
        full_quality=full_quality,
        restore_faces=restore_faces,
        tiling=tiling,
        init_images=[image],
        mask=mask,
        mask_blur=mask_blur,
        inpainting_fill=inpainting_fill,
        resize_mode=resize_mode,
        denoising_strength=denoising_strength,
        image_cfg_scale=image_cfg_scale,
        diffusers_guidance_rescale=diffusers_guidance_rescale,
        refiner_start=refiner_start,
        inpaint_full_res=inpaint_full_res,
        inpaint_full_res_padding=inpaint_full_res_padding,
        inpainting_mask_invert=inpainting_mask_invert,
        override_settings=override_settings,
    )
    p.scripts = modules.scripts.scripts_img2img
    p.script_args = args
    p.extra_generation_params['Resize mode'] = resize_mode
    if mask:
        p.extra_generation_params["Mask blur"] = mask_blur
    if is_batch:
        process_batch(p, img2img_batch_files, img2img_batch_input_dir, img2img_batch_output_dir, img2img_batch_inpaint_mask_dir, args)
        processed = processing.Processed(p, [], p.seed, "")
    else:
        processed = modules.scripts.scripts_img2img.run(p, *args)
        if processed is None:
            processed = processing.process_images(p)
    p.close()
    generation_info_js = processed.js()
    shared.log.debug(f'Processed: {len(processed.images)} Memory: {memory_stats()} img')
    return processed.images, generation_info_js, processed.info, plaintext_to_html(processed.comments)
