# Change Log for SD.Next

## Update for 2023-08-21

- general:
  - all system and image paths are now relative by default
  - fix extra networks previews
  - add settings validation when performing load/save

## Update for 2023-08-20

Another release thats been baking in dev branch for a while...

- general:
  - caching of extra network information to enable much faster create/refresh operations  
    thanks @midcoastal
- diffusers:
  - add **hires** support (*experimental*)  
    applies to all model types that support img2img, including **sd** and **sd-xl**  
    also supports all hires upscaler types as well as standard params like steps and denoising strength  
    when used with **sd-xl**, it can be used with or without refiner loaded  
    how to enable - there are no explicit checkboxes other than second pass itself:
    - hires: upscaler is set and target resolution is not at default  
    - refiner: if refiner model is loaded  
  - images save options: *before hires*, *before refiner*
  - redo `move model to cpu` logic in settings -> diffusers to be more reliable  
    note that system defaults have also changed, so you may need to tweak to your liking  
  - update dependencies

## Update for 2023-08-17

Smaller update, but with some breaking changes (to prepare for future larger functionality)...

- general:
  - update all metadata saved with images  
    see <https://github.com/vladmandic/automatic/wiki/Metadata> for details  
  - improved **amd** installer with support for **navi 2x & 3x** and **rocm 5.4/5.5/5.6**  
    thanks @evshiron  
  - fix **img2img** resizing (applies to *original, diffusers, hires*)  
  - config change: main `config.json` no longer contains entire configuration  
    but only differences from defaults (simmilar to recent change performed to `ui-config.json`)  
- diffusers:
  - enable **batch img2img** workflows  
- original:  
  - new samplers: **dpm++ 3M sde** (standard and karras variations)  
    enable in *settings -> samplers -> show samplers*
  - expose always/never discard penultimage sigma  
    enable in *settings -> samplers*  

## Update for 2023-08-11

This is a big one that's been cooking in `dev` for a while now, but finally ready for release...

- diffusers:
  - **pipeline autodetect**
    if pipeline is set to autodetect (default for new installs), app will try to autodetect pipeline based on selected model  
    this should reduce user errors such as loading **sd-xl** model when **sd** pipeline is selected  
  - **quick vae decode** as alternative to full vae decode which is very resource intensive  
    quick decode is based on `taesd` and produces lower quality, but its great for tests or grids as it runs much faster and uses far less vram  
    disabled by default, selectable in *txt2img/img2img -> advanced -> full quality*  
  - **prompt attention** for sd and sd-xl  
    supports both `full parser` and native `compel`  
    thanks @ai-casanova  
  - advanced **lora load/apply** methods  
    in addition to standard lora loading that was recently added to sd-xl using diffusers, now we have  
    - **sequential apply** (load & apply multiple loras in sequential manner) and  
    - **merge and apply** (load multiple loras and merge before applying to model)  
    see *settings -> diffusers -> lora methods*  
    thanks @hameerabbasi and @ai-casanova  
  - **sd-xl vae** from safetensors now applies correct config  
    result is that 3rd party vaes can be used without washed out colors  
  - options for optimized memory handling for lower memory usage  
    see *settings -> diffusers*
- general:
  - new **civitai model search and download**  
    native support for civitai, integrated into ui as *models -> civitai*  
  - updated requirements  
    this time its a bigger change so upgrade may take longer to install new requirements
  - improved **extra networks** performance with large number of networks

## Update for 2023-08-05

Another minor update, but it unlocks some cool new items...

- diffusers:
  - vaesd live preview (sd and sd-xl)  
  - fix inpainting (sd and sd-xl)  
- general:
  - new torch 2.0 with ipex (intel arc)  
  - additional callbacks for extensions  
    enables latest comfyui extension  

## Update for 2023-07-30

Smaller release, but IMO worth a post...

- diffusers:
  - sd-xl lora's are now supported!
  - memory optimizations: Enhanced sequential CPU offloading, model CPU offload, FP16 VAE
    - significant impact if running SD-XL (for example, but applies to any model) with only 8GB VRAM
  - update packages
- minor bugfixes

## Update for 2023-07-26

This is a big one, new models, new diffusers, new features and updated UI...

First, **SD-XL 1.0** is released and yes, SD.Next supports it out of the box!

- [SD-XL Base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/sd_xl_base_1.0.safetensors)
- [SD-XL Refiner](https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/blob/main/sd_xl_refiner_1.0.safetensors)

Also fresh is new **Kandinsky 2.2** model that does look quite nice:

- [Kandinsky Decoder](https://huggingface.co/kandinsky-community/kandinsky-2-2-decoder)
- [Kandinsky Prior](https://huggingface.co/kandinsky-community/kandinsky-2-2-prior)

Actual changelog is:

- general:
  - new loading screens and artwork
  - major ui simplification for both txt2img and img2img  
    nothing is removed, but you can show/hide individual sections  
    default is very simple interface, but you can enable any sections and save it as default in settings  
  - themes: add additional built-in theme, `amethyst-nightfall`
  - extra networks: add add/remove tags to prompt (e.g. lora activation keywords)
  - extensions: fix couple of compatibility items
  - firefox compatibility improvements
  - minor image viewer improvements
  - add backend and operation info to metadata

- diffusers:
  - we're out of experimental phase and diffusers backend is considered stable  
  - sd-xl: support for **sd-xl 1.0** official model
  - sd-xl: loading vae now applies to both base and refiner and saves a bit of vram  
  - sd-xl: denoising_start/denoising_end
  - sd-xl: enable dual prompts  
    dual prompt is used if set regardless if refiner is enabled/loaded  
    if refiner is loaded & enabled, refiner prompt will also be used for refiner pass  
    - primary prompt goes to [OpenAI CLIP-ViT/L-14](https://huggingface.co/openai/clip-vit-large-patch14)
    - refiner prompt goes to [OpenCLIP-ViT/bigG-14](https://huggingface.co/laion/CLIP-ViT-bigG-14-laion2B-39B-b160k)
  - **kandinsky 2.2** support  
    note: kandinsky model must be downloaded using model downloader, not as safetensors due to specific model format  
  - refiner: fix batch processing
  - vae: enable loading of pure-safetensors vae files without config  
    also enable *automatic* selection to work with diffusers  
  - sd-xl: initial lora support  
    right now this applies to official lora released by **stability-ai**, support for **kohya's** lora is expected soon  
  - implement img2img and inpainting (experimental)  
    actual support and quality depends on model  
    it works as expected for sd 1.5, but not so much for sd-xl for now  
  - implement limited stop/interrupt for diffusers
    works between stages, not within steps  
  - add option to save image before refiner pass  
  - option to set vae upcast in settings  
  - enable fp16 vae decode when using optimized vae  
    this pretty much doubles performance of decode step (delay after generate is done)  

- original
  - fix hires secondary sampler  
    this now fully obsoletes `fallback_sampler` and `force_latent_sampler`  


## Update for 2023-07-18

While we're waiting for official SD-XL release, here's another update with some fixes and enhancements...

- **global**
  - image save: option to add invisible image watermark to all your generated images  
    disabled by default, can be enabled in settings -> image options  
    watermark information will be shown when loading image such as in process image tab  
    also additional cli utility `/cli/image-watermark.py` to read/write/strip watermarks from images  
  - batch processing: fix metadata saving, also allow to drag&drop images for batch processing  
  - ui configuration: you can modify all ui default values from settings as usual,  
    but only values that are non-default will be written to `ui-config.json`  
  - startup: add cmd flag to skip all `torch` checks  
  - startup: force requirements check on each server start  
    there are too many misbehaving extensions that change system requirements  
  - internal: safe handling of all config file read/write operations  
    this allows sdnext to run in fully shared environments and prevents any possible configuration corruptions  
- **diffusers**:
  - sd-xl: remove image watermarks autocreated by 0.9 model  
  - vae: enable loading of external vae, documented in diffusers wiki  
    and mix&match continues, you can even use sd-xl vae with sd 1.5 models!  
  - samplers: add concept of *default* sampler to avoid needing to tweak settings for primary or second pass  
    note that sampler details will be printed in log when running in debug level  
  - samplers: allow overriding of sampler beta values in settings  
  - refiner: fix refiner applying only to first image in batch  
  - refiner: allow using direct latents or processed output in refiner  
  - model: basic support for one more model: [UniDiffuser](https://github.com/thu-ml/unidiffuser)  
    download using model downloader: `thu-ml/unidiffuser-v1`  
    and set resolution to 512x512  

## Update for 2023-07-14

Trying to unify settings for both original and diffusers backend without introducing duplicates...

- renamed **hires fix** to **second pass**  
  as that is what it actually is, name hires fix is misleading to start with  
- actual **hires fix** and **refiner** are now options inside **second pass** section  
- obsoleted settings -> sampler -> **force_latent_sampler**  
  it is now part of **second pass** options and it works the same for both original and diffusers backend  
  which means you can use different scheduler settings for txt2img and hires if you want  
- sd-xl refiner will run if its loaded and if second pass is enabled  
  so you can quickly enable/disable refiner by simply enabling/disabling second pass  
- you can mix&match **model** and **refiner**  
  for example, you can generate image using sd 1.5 and still use sd-xl refiner as second pass  
- reorganized settings -> samplers to show which section refers to which backend  
- added diffusers **lmsd** sampler  

## Update for 2023-07-13

Another big one, but now improvements to both **diffusers** and **original** backends as well plus ability to dynamically switch between them!

- swich backend between diffusers and original on-the-fly
  - you can still use `--backend <backend>` and now that only means in which mode app will start,
    but you can change it anytime in ui settings
  - for example, you can even do things like generate image using sd-xl,  
    then switch to original backend and perform inpaint using a different model  
- diffusers backend:
  - separate ui settings for refiner pass with sd-xl  
    you can specify: prompt, negative prompt, steps, denoise start  
  - fix loading from pure safetensors files  
    now you can load sd-xl from safetensors file or from huggingface folder format  
  - fix kandinsky model (2.1 working, 2.2 was just released and will be soon)  
- original backend:
  - improvements to vae/unet handling as well as cross-optimization heads  
    in non-technical terms, this means lower memory usage and higher performance  
    and you should be able to generate higher resolution images without any other changes
- other:
  - major refactoring of the javascript code  
    includes fixes for text selections and navigation  
  - system info tab now reports on nvidia driver version as well  
  - minor fixes in extra-networks  
  - installer handles origin changes for submodules  

big thanks to @huggingface team for great communication, support and fixing all the reported issues asap!


## Update for 2023-07-10

Service release with some fixes and enhancements:

- diffusers:
  - option to move base and/or refiner model to cpu to free up vram  
  - model downloader options to specify model variant / revision / mirror  
  - now you can download `fp16` variant directly for reduced memory footprint  
  - basic **img2img** workflow (*sketch* and *inpaint* are not supported yet)  
    note that **sd-xl** img2img workflows are architecturaly different so it will take longer to implement  
  - updated hints for settings  
- extra networks:
  - fix corrupt display on refesh when new extra network type found  
  - additional ui tweaks  
  - generate thumbnails from previews only if preview resolution is above 1k
- image viewer:
  - fixes for non-chromium browsers and mobile users and add option to download image  
  - option to download image directly from image viewer
- general
  - fix startup issue with incorrect config  
  - installer should always check requirements on upgrades

## Update for 2023-07-08

This is a massive update which has been baking in a `dev` branch for a while now

- merge experimental diffusers support  

*TL;DR*: Yes, you can run **SD-XL** model in **SD.Next** now  
For details, see Wiki page: [Diffusers](https://github.com/vladmandic/automatic/wiki/Diffusers)  
Note this is still experimental, so please follow Wiki  
Additional enhancements and fixes will be provided over the next few days  
*Thanks to @huggingface team for making this possible and our internal @team for all the early testing*

Release also contains number of smaller updates:

- add pan & zoom controls (touch and mouse) to image viewer (lightbox)  
- cache extra networks between tabs  
  this should result in neat 2x speedup on building extra networks  
- add settings -> extra networks -> do not automatically build extra network pages  
  speeds up app start if you have a lot of extra networks and you want to build them manually when needed  
- extra network ui tweaks  

## Update for 2023-07-01

Small quality-of-life updates and bugfixes:

- add option to disallow usage of ckpt checkpoints
- change lora and lyco dir without server restart
- additional filename template fields: `uuid`, `seq`, `image_hash`  
- image toolbar is now shown only when image is present
- image `Zip` button gone and its not optional setting that applies to standard `Save` button
- folder `Show` button is present only when working on localhost,  
  otherwise its replaced with `Copy` that places image URLs on clipboard so they can be used in other apps

## Update for 2023-06-30

A bit bigger update this time, but contained to specific areas...

- change in behavior  
  extensions no longer auto-update on startup  
  using `--upgrade` flag upgrades core app as well as all submodules and extensions  
- **live server log monitoring** in ui  
  configurable via settings -> live preview  
- new **extra networks interface**  
  *note: if you're using a 3rd party ui extension for extra networks, it will likely need to be updated to work with new interface*
  - display in front of main ui, inline with main ui or as a sidebar  
  - lazy load thumbnails  
    drastically reduces load times for large number of extra networks  
  - auto-create thumbnails from preview images in extra networks in a background thread  
    significant load time saving on subsequent restarts  
  - support for info files in addition to description files  
  - support for variable aspect-ratio thumbnails  
  - new folder view  
- **extensions sort** by trending  
- add requirements check for training  

## Update for 2023-06-26

- new training tab interface  
  - redesigned preprocess, train embedding, train hypernetwork  
- new models tab interface  
  - new model convert functionality, thanks @akegarasu  
  - new model verify functionality  
- lot of ipex specific fixes/optimizations, thanks @disty0  

## Update for 2023-06-20

This one is less relevant for standard users, but pretty major if you're running an actual server  
But even if not, it still includes bunch of cumulative fixes since last release - and going by number of new issues, this is probably the most stable release so far...
(next one is not going to be as stable, but it will be fun :) )

- minor improvements to extra networks ui  
- more hints/tooltips integrated into ui  
- new dedicated api server  
  - but highly promising for high throughput server  
- improve server logging and monitoring with  
  - server log file rotation  
  - ring buffer with api endpoint `/sdapi/v1/log`  
  - real-time status and load endpoint `/sdapi/v1/system-info/status`

## Update for 2023-06-14

Second stage of a jumbo merge from upstream plus few minor changes...

- simplify token merging  
- reorganize some settings  
- all updates from upstream: **A1111** v1.3.2 [df004be] *(latest release)*  
  pretty much nothing major that i haven't released in previous versions, but its still a long list of tiny changes  
  - skipped/did-not-port:  
    add separate hires prompt: unnecessarily complicated and spread over large number of commits due to many regressions  
    allow external scripts to add cross-optimization methods: dangerous and i don't see a use case for it so far  
    load extension info in threads: unnecessary as other optimizations i've already put place perform equally good  
  - broken/reverted:  
    sub-quadratic optimization changes  

## Update for 2023-06-13

Just a day later and one *bigger update*...
Both some **new functionality** as well as **massive merges** from upstream  

- new cache for models/lora/lyco metadata: `metadata.json`  
  drastically reduces disk access on app startup  
- allow saving/resetting of **ui default values**  
  settings -> ui defaults
- ability to run server without loaded model  
  default is to auto-load model on startup, can be changed in settings -> stable diffusion  
  if disabled, model will be loaded on first request, e.g. when you click generate  
  useful when you want to start server to perform other tasks like upscaling which do not rely on model  
- updated `accelerate` and `xformers`
- huge nubmer of changes ported from **A1111** upstream  
  this was a massive merge, hopefully this does not cause any regressions  
  and still a bit more pending...

## Update for 2023-06-12

- updated ui labels and hints to improve clarity and provide some extra info  
  this is 1st stage of the process, more to come...  
  if you want to join the effort, see <https://github.com/vladmandic/automatic/discussions/1246>
- new localization and hints engine  
  how hints are displayed can be selected in settings -> ui  
- reworked **installer** sequence  
  as some extensions are loading packages directly from their preload sequence  
  which was preventing some optimizations to take effect  
- updated **settings** tab functionality, thanks @gegell  
  with real-time monitor for all new and/or updated settings  
- **launcher** will now warn if application owned files are modified  
  you are free to add any user files, but do not modify app files unless you're sure in what you're doing  
- add more profiling for scripts/extensions so you can see what takes time  
  this applies both to initial load as well as execution  
- experimental `sd_model_dict` setting which allows you to load model dictionary  
  from one model and apply weights from another model specified in `sd_model_checkpoint`  
  results? who am i to judge :)


## Update for 2023-06-05

Few new features and extra handling for broken extensions  
that caused my phone to go crazy with notifications over the weekend...

- added extra networks to **xyz grid** options  
  now you can have more fun with all your embeddings and loras :)  
- new **vae decode** method to help with larger batch sizes, thanks @bigdog  
- new setting -> lora -> **use lycoris to handle all lora types**  
  this is still experimental, but the goal is to obsolete old built-in lora module  
  as it doesn't understand many new loras and built-in lyco module can handle it all  
- somewhat optimize browser page loading  
  still slower than i'd want, but gradio is pretty bad at this  
- profiling of scripts/extensions callbacks  
  you can now see how much or pre/post processing is done, not just how long generate takes  
- additional exception handling so bad exception does not crash main app  
- additional background removal models  
- some work on bfloat16 which nobody really should be using, but why not 🙂


## Update for 2023-06-02

Some quality-of-life improvements while working on larger stuff in the background...

- redesign action box to be uniform across all themes  
- add **pause** option next to stop/skip  
- redesigned progress bar  
- add new built-in extension: **agent-scheduler**  
  very elegant way to getting full queueing capabilities, thank @artventurdev  
- enable more image formats  
  note: not all are understood by browser so previews and images may appear as blank  
  unless you have some browser extensions that can handle them  
  but they are saved correctly. and cant beat raw quality of 32-bit `tiff` or `psd` :)  
- change in behavior: `xformers` will be uninstalled on startup if they are not active  
  if you do have `xformers` selected as your desired cross-optimization method, then they will be used  
  reason is that a lot of libaries try to blindly import xformers even if they are not selected or not functional  

## Update for 2023-05-30

Another bigger one...And more to come in the next few days...

- new live preview mode: taesd  
  i really like this one, so its enabled as default for new installs  
- settings search feature  
- new sampler: dpm++ 2m sde  
- fully common save/zip/delete (new) options in all tabs  
  which (again) meant rework of process image tab  
- system info tab: live gpu utilization/memory graphs for nvidia gpus  
- updated controlnet interface  
- minor style changes  
- updated lora, swinir, scunet and ldsr code from upstream  
- start of merge from a1111 v1.3  

## Update for 2023-05-26

Some quality-of-life improvements...

- updated [README](https://github.com/vladmandic/automatic/blob/master/README.md)
- created [CHANGELOG](https://github.com/vladmandic/automatic/blob/master/CHANGELOG.md)  
  this will be the source for all info about new things moving forward  
  and cross-posted to [Discussions#99](https://github.com/vladmandic/automatic/discussions/99) as well as discord [announcements](https://discord.com/channels/1101998836328697867/1109953953396957286)
- optimize model loading on startup  
  this should reduce startup time significantly  
- set default cross-optimization method for each platform backend  
  applicable for new installs only  
  - `cuda` => Scaled-Dot-Product
  - `rocm` => Sub-quadratic
  - `directml` => Sub-quadratic
  - `ipex` => InvokeAI's
  - `mps` => Doggettx's
  - `cpu` => Doggettx's
- optimize logging  
- optimize profiling  
  now includes startup profiling as well as `cuda` profiling during generate  
- minor lightbox improvements  
- bugfixes...i don't recall when was a release with at least several of those  

other than that - first stage of [Diffusers](https://github.com/huggingface/diffusers) integration is now in master branch  
i don't recommend anyone to try it (and dont even think reporting issues for it)  
but if anyone wants to contribute, take a look at [project page](https://github.com/users/vladmandic/projects/1/views/1)

## Update for 2023-05-23

Major internal work with perhaps not that much user-facing to show for it ;)

- update core repos: **stability-ai**, **taming-transformers**, **k-diffusion, blip**, **codeformer**  
  note: to avoid disruptions, this is applicable for new installs only
- tested with **torch 2.1**, **cuda 12.1**, **cudnn 8.9**  
  (production remains on torch2.0.1+cuda11.8+cudnn8.8)  
- fully extend support of `--data-dir`  
  allows multiple installations to share pretty much everything, not just models  
  especially useful if you want to run in a stateless container or cloud instance  
- redo api authentication  
  now api authentication will use same user/pwd (if specified) for ui and strictly enforce it using httpbasicauth  
  new authentication is also fully supported in combination with ssl for both sync and async calls  
  if you want to use api programatically, see examples in `cli/sdapi.py`  
- add dark/light theme mode toggle  
- redo some `clip-skip` functionality  
- better matching for vae vs model  
- update to `xyz grid` to allow creation of large number of images without creating grid itself  
- update `gradio` (again)  
- more prompt parser optimizations  
- better error handling when importing image settings which are not compatible with current install  
  for example, when upscaler or sampler originally used is not available  
- fixes...amazing how many issues were introduced by porting a1111 v1.20 code without adding almost no new functionality  
  next one is v1.30 (still in dev) which does bring a lot of new features  

## Update for 2023-05-17

This is a massive one due to huge number of changes,  
but hopefully it will go ok...

- new **prompt parsers**  
  select in UI -> Settings -> Stable Diffusion  
  - **Full**: my new implementation  
  - **A1111**: for backward compatibility  
  - **Compel**: as used in ComfyUI and InvokeAI (a.k.a *Temporal Weighting*)  
  - **Fixed**: for really old backward compatibility  
- monitor **extensions** install/startup and  
  log if they modify any packages/requirements  
  this is a *deep-experimental* python hack, but i think its worth it as extensions modifying requirements  
  is one of most common causes of issues
- added `--safe` command line flag mode which skips loading user extensions  
  please try to use it before opening new issue  
- reintroduce `--api-only` mode to start server without ui  
- port *all* upstream changes from [A1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  
  up to today - commit hash `89f9faa`  

## Update for 2023-05-15

- major work on **prompt parsing**
  this can cause some differences in results compared to what you're used to, but its all about fixes & improvements
  - prompt parser was adding commas and spaces as separate words and tokens and/or prefixes
  - negative prompt weight using `[word:weight]` was ignored, it was always `0.909`
  - bracket matching was anything but correct. complex nested attention brackets are now working.
  - btw, if you run with `--debug` flag, you'll now actually see parsed prompt & schedule
- updated all scripts in `/cli`  
- add option in settings to force different **latent sampler** instead of using primary only
- add **interrupt/skip** capabilities to process images

## Update for 2023-05-13

This is mostly about optimizations...

- improved `torch-directml` support  
  especially interesting for **amd** users on **windows**  where **torch+rocm** is not yet available  
  dont forget to run using `--use-directml` or default is **cpu**  
- improved compatibility with **nvidia** rtx 1xxx/2xxx series gpus  
- fully working `torch.compile` with **torch 2.0.1**  
  using `inductor` compile takes a while on first run, but does result in 5-10% performance increase  
- improved memory handling  
  for highest performance, you can also disable aggressive **gc** in settings  
- improved performance  
  especially *after* generate as image handling has been moved to separate thread  
- allow per-extension updates in extension manager  
- option to reset configuration in settings  

## Update for 2023-05-11

- brand new **extension manager**  
  this is pretty much a complete rewrite, so new issues are possible
- support for `torch` 2.0.1  
  note that if you are experiencing frequent hangs, this may be a worth a try  
- updated `gradio` to 3.29.0
- added `--reinstall` flag to force reinstall of all packages  
- auto-recover & re-attempt when `--upgrade` is requested but fails
- check for duplicate extensions  

## Update for 2023-05-08

Back online with few updates:

- bugfixes. yup, quite a lot of those  
- auto-detect some cpu/gpu capabilities on startup  
  this should reduce need to tweak and tune settings like no-half, no-half-vae, fp16 vs fp32, etc  
- configurable order of top level tabs  
- configurable order of scripts in txt2img and img2img  
  for both, see sections in ui-> settings -> user interface

## Update for 2023-05-04

Again, few days later...

- reviewed/ported **all** commits from **A1111** upstream  
  some a few are not applicable as i already have alternative implementations  
  and very few i choose not to implement (save/restore last-known-good-config is a bad hack)  
  otherwise, we're fully up to date (its doesn't show on fork status as code merges were mostly manual due to conflicts)  
  but...due to sheer size of the updates, this may introduce some temporary issues  
- redesigned server restart function  
  now available and working in ui  
  actually, since server restart is now a true restart and not ui restart, it can be used much more flexibly  
- faster model load  
  plus support for slower devices via stream-load function (in ui settings)  
- better logging  
  this includes new `--debug` flag for more verbose logging when troubleshooting  

## Update for 2023-05-01

Been a bit quieter for last few days as changes were quite significant, but finally here we are...

- Updated core libraries: Gradio, Diffusers, Transformers
- Added support for **Intel ARC** GPUs via Intel OneAPI IPEX (auto-detected)
- Added support for **TorchML** (set by default when running on non-compatible GPU or on CPU)
- Enhanced support for AMD GPUs with **ROCm**
- Enhanced support for Apple **M1/M2**
- Redesigned command params: run `webui --help` for details
- Redesigned API and script processing
- Experimental support for multiple **Torch compile** options
- Improved sampler support
- Google Colab: <https://colab.research.google.com/drive/126cDNwHfifCyUpCCQF9IHpEdiXRfHrLN>  
  Maintained by <https://github.com/Linaqruf/sd-notebook-collection>
- Fixes, fixes, fixes...

To take advantage of new out-of-the-box tunings, its recommended to delete your `config.json` so new defaults are applied. Its not necessary, but otherwise you may need to play with UI Settings to get the best of Intel ARC, TorchML, ROCm or Apple M1/M2.

## Update for 2023-04-27

a bit shorter list as:

- i've been busy with bugfixing  
  there are a lot of them, not going to list each here.  
  but seems like critical issues backlog is quieting down and soon i can focus on new features development.  
- i've started collaboration with couple of major projects,
  hopefully this will accelerate future development.

what's new:

- ability to view/add/edit model description shown in extra networks cards  
- add option to specify fallback sampler if primary sampler is not compatible with desired operation  
- make clip skip a local parameter  
- remove obsolete items from UI settings  
- set defaults for AMD ROCm  
  if you have issues, you may want to start with a fresh install so configuration can be created from scratch
- set defaults for Apple M1/M2  
  if you have issues, you may want to start with a fresh install so configuration can be created from scratch

## Update for 2023-04-25

- update process image -> info
- add VAE info to metadata
- update GPU utility search paths for better GPU type detection
- update git flags for wider compatibility
- update environment tuning
- update ti training defaults
- update VAE search paths
- add compatibility opts for some old extensions
- validate script args for always-on scripts  
  fixes: deforum with controlnet  

## Update for 2023-04-24

- identify race condition where generate locks up while fetching preview
- add pulldowns to x/y/z script
- add VAE rollback feature in case of NaNs
- use samples format for live preview
- add token merging
- use **Approx NN** for live preview
- create default `styles.csv`
- fix setup not installing `tensorflow` dependencies
- update default git flags to reduce number of warnings

## Update for 2023-04-23

- fix VAE dtype  
  should fix most issues with NaN or black images  
- add built-in Gradio themes  
- reduce requirements  
- more AMD specific work
- initial work on Apple platform support
- additional PR merges
- handle torch cuda crashing in setup
- fix setup race conditions
- fix ui lightbox
- mark tensorflow as optional
- add additional image name templates

## Update for 2023-04-22

- autodetect which system libs should be installed  
  this is a first pass of autoconfig for **nVidia** vs **AMD** environments  
- fix parse cmd line args from extensions  
- only install `xformers` if actually selected as desired cross-attention method
- do not attempt to use `xformers` or `sdp` if running on cpu
- merge tomesd token merging  
- merge 23 PRs pending from a1111 backlog (!!)

*expect shorter updates for the next few days as i'll be partially ooo*

## Update for 2023-04-20

- full CUDA tuning section in UI Settings
- improve exif/pnginfo metadata parsing  
  it can now handle 3rd party images or images edited in external software
- optimized setup performance and logging
- improve compatibility with some 3rd party extensions
  for example handle extensions that install packages directly from github urls
- fix initial model download if no models found
- fix vae not found issues
- fix multiple git issues

note: if you previously had command line optimizations such as --no-half, those are now ignored and moved to ui settings

## Update for 2023-04-19

- fix live preview
- fix model merge
- fix handling of user-defined temp folders
- fix submit benchmark
- option to override `torch` and `xformers` installer
- separate benchmark data for system-info extension
- minor css fixes
- created initial merge backlog from pending prs on a1111 repo  
  see #258 for details

## Update for 2023-04-18

- reconnect ui to active session on browser restart  
  this is one of most frequently asked for items, finally figured it out  
  works for text and image generation, but not for process as there is no progress bar reported there to start with  
- force unload `xformers` when not used  
  improves compatibility with AMD/M1 platforms  
- add `styles.csv` to UI settings to allow customizing path  
- add `--skip-git` to cmd flags for power users that want  
  to skip all git checks and operations and perform manual updates
- add `--disable-queue` to cmd flags that disables Gradio queues (experimental)
  this forces it to use HTTP instead of WebSockets and can help on unreliable network connections  
- set scripts & extensions loading priority and allow custom priorities  
  fixes random extension issues:  
  `ScuNet` upscaler disappearing, `Additional Networks` not showing up on XYZ axis, etc.
- improve html loading order
- remove some `asserts` causing runtime errors and replace with user-friendly messages
- update README.md
- update TODO.md

## Update for 2023-04-17

- **themes** are now dynamic and discovered from list of available gradio themes on huggingface  
  its quite a list of 30+ supported themes so far  
- added option to see **theme preview** without the need to apply it or restart server
- integrated **image info** functionality into **process image** tab and removed separate **image info** tab
- more installer improvements
- fix urls
- updated github integration
- make model download as optional if no models found

## Update for 2023-04-16

- support for ui themes! to to *settings* -> *user interface* -> "ui theme*
  includes 12 predefined themes
- ability to restart server from ui
- updated requirements
- removed `styles.csv` from repo, its now fully under user control
- removed model-keyword extension as overly aggressive
- rewrite of the fastapi middleware handlers
- install bugfixes, hopefully new installer is now ok  \
  i really want to focus on features and not troubleshooting installer

## Update for 2023-04-15

- update default values
- remove `ui-config.json` from repo, its not fully under user control
- updated extensions manager
- updated locon/lycoris plugin
- enable quick launch by default
- add multidiffusion upscaler extensions
- add model keyword extension
- enable strong linting
- fix circular imports
- fix extensions updated
- fix git update issues
- update github templates

## Update for 2023-04-14

- handle duplicate extensions
- redo exception handler
- fix generate forever
- enable cmdflags compatibility
- change default css font
- fix ti previews on initial start
- enhance tracebacks
- pin transformers version to last known good version
- fix extension loader

## Update for 2023-04-12

This has been pending for a while, but finally uploaded some massive changes

- New launcher
  - `webui.bat` and `webui.sh`:  
    Platform specific wrapper scripts that starts `launch.py` in Python virtual environment  
    *Note*: Server can run without virtual environment, but it is recommended to use it  
    This is carry-over from original repo  
    **If you're unsure which launcher to use, this is the one you want**  
  - `launch.py`:  
    Main startup script  
    Can be used directly to start server in manually activated `venv` or to run it without `venv`  
  - `installer.py`:  
    Main installer, used by `launch.py`  
  - `webui.py`:  
    Main server script  
- New logger
- New exception handler
- Built-in performance profiler
- New requirements handling
- Move of most of command line flags into UI Settings
