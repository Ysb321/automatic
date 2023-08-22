import os
import sys
import json
import time
import shutil
import logging
import platform
import subprocess
import io
import pstats
import cProfile
import pkg_resources


class Dot(dict): # dot notation access to dictionary attributes
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


log = logging.getLogger("sd")
log_file = os.path.join(os.path.dirname(__file__), 'sdnext.log')
quick_allowed = True
errors = 0
opts = {}
args = Dot({
    'debug': False,
    'reset': False,
    'upgrade': False,
    'skip_extensions': False,
    'skip_requirements': False,
    'skip_git': False,
    'skip_torch': False,
    'use_directml': False,
    'use_ipex': False,
    'use_cuda': False,
    'use_rocm': False,
    'experimental': False,
    'test': False,
    'tls_selfsign': False,
    'reinstall': False,
    'version': False,
    'ignore': False,
})
git_commit = "unknown"


# setup console and file logging
def setup_logging():

    class RingBuffer(logging.StreamHandler):
        def __init__(self, capacity):
            super().__init__()
            self.capacity = capacity
            self.buffer = []
            self.formatter = logging.Formatter('{ "asctime":"%(asctime)s", "created":%(created)f, "facility":"%(name)s", "pid":%(process)d, "tid":%(thread)d, "level":"%(levelname)s", "module":"%(module)s", "func":"%(funcName)s", "msg":"%(message)s" }')

        def emit(self, record):
            msg = self.format(record)
            # self.buffer.append(json.loads(msg))
            self.buffer.append(msg)
            if len(self.buffer) > self.capacity:
                self.buffer.pop(0)

        def get(self):
            return self.buffer

    from logging.handlers import RotatingFileHandler
    from rich.theme import Theme
    from rich.logging import RichHandler
    from rich.console import Console
    from rich.pretty import install as pretty_install
    from rich.traceback import install as traceback_install

    level = logging.DEBUG if args.debug else logging.INFO
    log.setLevel(logging.DEBUG) # log to file is always at level debug for facility `sd`
    console = Console(log_time=True, log_time_format='%H:%M:%S-%f', theme=Theme({
        "traceback.border": "black",
        "traceback.border.syntax_error": "black",
        "inspect.value.border": "black",
    }))
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(message)s', handlers=[logging.NullHandler()]) # redirect default logger to null
    pretty_install(console=console)
    traceback_install(console=console, extra_lines=1, max_frames=10, width=console.width, word_wrap=False, indent_guides=False, suppress=[])
    while log.hasHandlers() and len(log.handlers) > 0:
        log.removeHandler(log.handlers[0])

    # handlers
    rh = RichHandler(show_time=True, omit_repeated_times=False, show_level=True, show_path=False, markup=False, rich_tracebacks=True, log_time_format='%H:%M:%S-%f', level=level, console=console)
    rh.setLevel(level)
    log.addHandler(rh)

    fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8', delay=True) # 10MB default for log rotation
    fh.formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(message)s')
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)

    rb = RingBuffer(100) # 100 entries default in log ring buffer
    rb.setLevel(level)
    log.addHandler(rb)
    log.buffer = rb.buffer

    # overrides
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("ControlNet").handlers = log.handlers
    logging.getLogger("lycoris").handlers = log.handlers
    # logging.getLogger("DeepSpeed").handlers = log.handlers


def print_profile(profile: cProfile.Profile, msg: str):
    try:
        from rich import print # pylint: disable=redefined-builtin
    except Exception:
        pass
    profile.disable()
    stream = io.StringIO()
    ps = pstats.Stats(profile, stream=stream)
    ps.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(15)
    profile = None
    lines = stream.getvalue().split('\n')
    lines = [line for line in lines if '<frozen' not in line and '{built-in' not in line and '/logging' not in line and '/rich' not in line]
    print(f'Profile {msg}:', '\n'.join(lines))


# check if package is installed
def installed(package, friendly: str = None):
    ok = True
    try:
        if friendly:
            pkgs = friendly.split()
        else:
            pkgs = [p for p in package.split() if not p.startswith('-') and not p.startswith('=')]
            pkgs = [p.split('/')[-1] for p in pkgs] # get only package name if installing from url
        for pkg in pkgs:
            if '>=' in pkg:
                p = pkg.split('>=')
            else:
                p = pkg.split('==')
            spec = pkg_resources.working_set.by_key.get(p[0], None) # more reliable than importlib
            if spec is None:
                spec = pkg_resources.working_set.by_key.get(p[0].lower(), None) # check name variations
            if spec is None:
                spec = pkg_resources.working_set.by_key.get(p[0].replace('_', '-'), None) # check name variations
            ok = ok and spec is not None
            if ok:
                version = pkg_resources.get_distribution(p[0]).version
                # log.debug(f"Package version found: {p[0]} {version}")
                if len(p) > 1:
                    exact = version == p[1]
                    ok = ok and (exact or args.experimental)
                    if not exact:
                        if args.experimental:
                            log.warning(f"Package allowing experimental: {p[0]} {version} required {p[1]}")
                        else:
                            log.warning(f"Package wrong version: {p[0]} {version} required {p[1]}")
            else:
                log.debug(f"Package version not found: {p[0]}")
        return ok
    except ModuleNotFoundError:
        log.debug(f"Package not installed: {pkgs}")
        return False


def pip(arg: str, ignore: bool = False, quiet: bool = False):
    arg = arg.replace('>=', '==')
    if not quiet:
        log.info(f'Installing package: {arg.replace("install", "").replace("--upgrade", "").replace("--no-deps", "").replace("--force", "").replace("  ", " ").strip()}')
    env_args = os.environ.get("PIP_EXTRA_ARGS", "")
    log.debug(f"Running pip: {arg} {env_args}")
    result = subprocess.run(f'"{sys.executable}" -m pip {arg} {env_args}', shell=True, check=False, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    txt = result.stdout.decode(encoding="utf8", errors="ignore")
    if len(result.stderr) > 0:
        txt += ('\n' if len(txt) > 0 else '') + result.stderr.decode(encoding="utf8", errors="ignore")
    txt = txt.strip()
    if result.returncode != 0 and not ignore:
        global errors # pylint: disable=global-statement
        errors += 1
        log.error(f'Error running pip: {arg}')
        log.debug(f'Pip output: {txt}')
    return txt


# install package using pip if not already installed
def install(package, friendly: str = None, ignore: bool = False):
    if args.reinstall or args.upgrade:
        global quick_allowed # pylint: disable=global-statement
        quick_allowed = False
    if args.reinstall or not installed(package, friendly):
        pip(f"install --upgrade {package}", ignore=ignore)


# execute git command
def git(arg: str, folder: str = None, ignore: bool = False):
    if args.skip_git:
        return ''
    git_cmd = os.environ.get('GIT', "git")
    if git_cmd != "git":
        git_cmd = os.path.abspath(git_cmd)
    result = subprocess.run(f'"{git_cmd}" {arg}', check=False, shell=True, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=folder or '.')
    txt = result.stdout.decode(encoding="utf8", errors="ignore")
    if len(result.stderr) > 0:
        txt += ('\n' if len(txt) > 0 else '') + result.stderr.decode(encoding="utf8", errors="ignore")
    txt = txt.strip()
    if result.returncode != 0 and not ignore:
        if "couldn't find remote ref" in txt: # not a git repo
            return txt
        global errors # pylint: disable=global-statement
        errors += 1
        log.error(f'Error running git: {folder} / {arg}')
        if 'or stash them' in txt:
            log.error(f'Local changes detected: check log for details: {log_file}')
        log.debug(f'Git output: {txt}')
    return txt

# switch to main branch as head can get detached
def branch(folder):
    if args.experimental:
        return None
    if not os.path.exists(os.path.join(folder, '.git')):
        return None
    b = git('branch', folder)
    if 'main' in b:
        b = 'main'
    elif 'master' in b:
        b = 'master'
    else:
        b = b.split('\n')[0].replace('*', '').strip()
    log.debug(f'Submodule: {folder} / {b}')
    git(f'checkout {b}', folder, ignore=True)
    return b


# update git repository
def update(folder, current_branch = False):
    try:
        git('config rebase.Autostash true')
    except Exception:
        pass
    if current_branch:
        git('pull --rebase --force', folder)
        return
    b = branch(folder)
    if branch is None:
        git('pull --rebase --force', folder)
    else:
        git(f'pull origin {b} --rebase --force', folder)


# clone git repository
def clone(url, folder, commithash=None):
    if os.path.exists(folder):
        if commithash is None:
            update(folder)
        else:
            current_hash = git('rev-parse HEAD', folder).strip()
            if current_hash != commithash:
                git('fetch', folder)
                git(f'checkout {commithash}', folder)
                return
    else:
        log.info(f'Cloning repository: {url}')
        git(f'clone "{url}" "{folder}"')
        if commithash is not None:
            git(f'-C "{folder}" checkout {commithash}')


# check python version
def check_python():
    supported_minors = [9, 10]
    if args.quick:
        return
    if args.experimental:
        supported_minors.append(11)
    log.info(f'Python {platform.python_version()} on {platform.system()}')
    if not (int(sys.version_info.major) == 3 and int(sys.version_info.minor) in supported_minors):
        log.error(f"Incompatible Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} required 3.{supported_minors}")
        if not args.ignore:
            sys.exit(1)
    if not args.skip_git:
        git_cmd = os.environ.get('GIT', "git")
        if shutil.which(git_cmd) is None:
            log.error('Git not found')
            if not args.ignore:
                sys.exit(1)
    else:
        git_version = git('--version', folder=None, ignore=False)
        log.debug(f'Git {git_version.replace("git version", "").strip()}')


# Intel hasn't released a corresponding torchvision wheel along with torch and ipex wheels, so we have to install official pytorch torchvision as a W/A.
# However, the latest torchvision explicitly requires torch version == 2.0.1, which is incompatible with the Intel torch version 2.0.0a0. This will cause
# intel torch to be uninstalled when pip scans the dependencies of torchvision. This function will check the torch version and force installing Intel torch
# 2.0.0a0 to avoid the underlying dll version error.
# TODO(Disty or Nuullll) remove this W/A when Intel releases torchvision wheel for windows.
def fix_ipex_win_torch():
    if not args.use_ipex or 'win' not in sys.platform:
        return
    try:
        ipex_torch_ver = '2.0.0a0'
        installed_torch_ver = pkg_resources.get_distribution('torch').version
        if not installed_torch_ver.startswith(ipex_torch_ver):
            log.warning(f'Incompatible torch version {installed_torch_ver} for ipex windows, reinstalling to {ipex_torch_ver}')
            torch_command = os.environ.get('TORCH_COMMAND', 'torch==2.0.0a0 intel_extension_for_pytorch==2.0.110+gitba7f6c1 -f https://developer.intel.com/ipex-whl-stable-xpu')
            install(torch_command)
            import torch # pylint: disable=unused-import
            import intel_extension_for_pytorch as ipex # pylint: disable=unused-import
    except Exception as e:
        log.warning(e)


# check torch version
def check_torch():
    if args.quick:
        return
    if args.skip_torch:
        log.info('Skipping Torch tests')
        return
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    allow_cuda = not (args.use_rocm or args.use_directml or args.use_ipex or args.use_openvino)
    allow_rocm = not (args.use_cuda or args.use_directml or args.use_ipex or args.use_openvino)
    allow_ipex = not (args.use_cuda or args.use_rocm or args.use_directml or args.use_openvino)
    allow_directml = not (args.use_cuda or args.use_rocm or args.use_ipex or args.use_openvino)
    allow_openvino = not (args.use_cuda or args.use_rocm or args.use_ipex or args.use_directml)
    log.debug(f'Torch overrides: cuda={args.use_cuda} rocm={args.use_rocm} ipex={args.use_ipex} diml={args.use_directml} openvino={args.use_openvino}')
    log.debug(f'Torch allowed: cuda={allow_cuda} rocm={allow_rocm} ipex={allow_ipex} diml={allow_directml} openvino={allow_openvino}')
    torch_command = os.environ.get('TORCH_COMMAND', '')
    xformers_package = os.environ.get('XFORMERS_PACKAGE', 'none')
    if torch_command != '':
        pass
    elif allow_cuda and (shutil.which('nvidia-smi') is not None or os.path.exists(os.path.join(os.environ.get('SystemRoot') or r'C:\Windows', 'System32', 'nvidia-smi.exe'))):
        log.info('nVidia CUDA toolkit detected')
        torch_command = os.environ.get('TORCH_COMMAND', 'torch torchvision --index-url https://download.pytorch.org/whl/cu118')
        xformers_package = os.environ.get('XFORMERS_PACKAGE', 'xformers==0.0.20' if opts.get('cross_attention_optimization', '') == 'xFormers' else 'none')
    elif allow_rocm and (shutil.which('rocminfo') is not None or os.path.exists('/opt/rocm/bin/rocminfo') or os.path.exists('/dev/kfd')):
        log.info('AMD ROCm toolkit detected')
        os.environ.setdefault('PYTORCH_HIP_ALLOC_CONF', 'garbage_collection_threshold:0.8,max_split_size_mb:512')
        os.environ.setdefault('TENSORFLOW_PACKAGE', 'tensorflow-rocm')
        try:
            command = subprocess.run('rocm_agent_enumerator', shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            amd_gpus = command.stdout.decode(encoding="utf8", errors="ignore").split('\n')
            amd_gpus = [x for x in amd_gpus if x and x != 'gfx000']
            log.debug(f'ROCm agents detected: {amd_gpus}')
        except Exception as e:
            log.debug(f'Run rocm_agent_enumerator failed: {e}')
            amd_gpus = []

        hip_visible_devices = [] # use the first available amd gpu by default
        for idx, gpu in enumerate(amd_gpus):
            if gpu in ['gfx1100', 'gfx1101', 'gfx1102']:
                hip_visible_devices.append((idx, gpu, 'navi3x'))
                break
            if gpu in ['gfx1030', 'gfx1031', 'gfx1032', 'gfx1034']: # experimental navi 2x support
                hip_visible_devices.append((idx, gpu, 'navi2x'))
                break
        if len(hip_visible_devices) > 0:
            idx, gpu, arch = hip_visible_devices[0]
            log.debug(f'ROCm agent used by default: idx={idx} gpu={gpu} arch={arch}')
            os.environ.setdefault('HIP_VISIBLE_DEVICES', str(idx))
            if arch == 'navi3x':
                os.environ.setdefault('HSA_OVERRIDE_GFX_VERSION', '11.0.0')
                if os.environ.get('TENSORFLOW_PACKAGE') == 'tensorflow-rocm': # do not use tensorflow-rocm for navi 3x
                    os.environ['TENSORFLOW_PACKAGE'] = 'tensorflow==2.13.0'
            elif arch == 'navi2x':
                os.environ.setdefault('HSA_OVERRIDE_GFX_VERSION', '10.3.0')
            else:
                log.debug(f'HSA_OVERRIDE_GFX_VERSION auto config is skipped for {gpu}')
        try:
            command = subprocess.run('hipconfig --version', shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            major_ver, minor_ver, *_ = command.stdout.decode(encoding="utf8", errors="ignore").split('.')
            rocm_ver = f'{major_ver}.{minor_ver}'
            log.debug(f'ROCm version detected: {rocm_ver}')
        except Exception as e:
            log.debug(f'Run hipconfig failed: {e}')
            rocm_ver = None
        if rocm_ver in ['5.5', '5.6']:
            # install torch nightly via torchvision to avoid wasting bandwidth when torchvision depends on torch from yesterday
            torch_command = os.environ.get('TORCH_COMMAND', f'torchvision --pre --index-url https://download.pytorch.org/whl/nightly/rocm{rocm_ver}')
        else:
            torch_command = os.environ.get('TORCH_COMMAND', 'torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/rocm5.4.2')
        xformers_package = os.environ.get('XFORMERS_PACKAGE', 'none')
    elif allow_ipex and (args.use_ipex or shutil.which('sycl-ls') is not None or shutil.which('sycl-ls.exe') is not None or os.environ.get('ONEAPI_ROOT') is not None or os.path.exists('/opt/intel/oneapi') or os.path.exists("C:/Program Files (x86)/Intel/oneAPI") or os.path.exists("C:/oneAPI")):
        args.use_ipex = True # pylint: disable=attribute-defined-outside-init
        log.info('Intel OneAPI Toolkit detected')
        if shutil.which('sycl-ls') is None and shutil.which('sycl-ls.exe') is None:
            log.error('Intel OneAPI Toolkit is not activated! Activate OneAPI manually!')
        os.environ.setdefault('NEOReadDebugKeys', '1')
        os.environ.setdefault('ClDeviceGlobalMemSizeAvailablePercent', '100')
        if "linux" in sys.platform:
            torch_command = os.environ.get('TORCH_COMMAND', 'torch==2.0.1a0 torchvision==0.15.2a0 intel_extension_for_pytorch==2.0.110+xpu -f https://developer.intel.com/ipex-whl-stable-xpu')
            os.environ.setdefault('TENSORFLOW_PACKAGE', 'tensorflow==2.13.0 intel-extension-for-tensorflow[gpu]')
        else:
            torch_command = os.environ.get('TORCH_COMMAND', 'torch==2.0.0a0 intel_extension_for_pytorch==2.0.110+gitba7f6c1 -f https://developer.intel.com/ipex-whl-stable-xpu')
    elif allow_openvino and args.use_openvino:
        #Remove this after 2.1.0 releases
        log.info('Using OpenVINO with Torch Nightly CPU')
        torch_command = os.environ.get('TORCH_COMMAND', '--pre torch==2.1.0.dev20230713+cpu torchvision==0.16.0.dev20230713+cpu -f https://download.pytorch.org/whl/nightly/cpu/torch_nightly.html')
    else:
        machine = platform.machine()
        if sys.platform == 'darwin':
            torch_command = os.environ.get('TORCH_COMMAND', 'torch==2.0.1 torchvision==0.15.2')
        elif allow_directml and args.use_directml and ('arm' not in machine and 'aarch' not in machine):
            log.info('Using DirectML Backend')
            torch_command = os.environ.get('TORCH_COMMAND', 'torch-directml')
            if 'torch' in torch_command and not args.version:
                install(torch_command, 'torch torchvision')
        else:
            log.info('Using CPU-only Torch')
            torch_command = os.environ.get('TORCH_COMMAND', 'torch torchvision')
    if 'torch' in torch_command and not args.version:
        install(torch_command, 'torch torchvision')
    else:
        try:
            import torch
            log.info(f'Torch {torch.__version__}')
            if args.use_ipex and allow_ipex:
                fix_ipex_win_torch()
                import intel_extension_for_pytorch as ipex # pylint: disable=import-error, unused-import
                log.info(f'Torch backend: Intel IPEX {ipex.__version__}')
                if shutil.which('icpx') is not None:
                    log.info(f'{os.popen("icpx --version").read().rstrip()}')
                for device in range(torch.xpu.device_count()):
                    log.info(f'Torch detected GPU: {torch.xpu.get_device_name(device)} VRAM {round(torch.xpu.get_device_properties(device).total_memory / 1024 / 1024)} Compute Units {torch.xpu.get_device_properties(device).max_compute_units}')
            elif torch.cuda.is_available() and (allow_cuda or allow_rocm):
                # log.debug(f'Torch allocator: {torch.cuda.get_allocator_backend()}')
                if torch.version.cuda and allow_cuda:
                    log.info(f'Torch backend: nVidia CUDA {torch.version.cuda} cuDNN {torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else "N/A"}')
                elif torch.version.hip and allow_rocm:
                    log.info(f'Torch backend: AMD ROCm HIP {torch.version.hip}')
                else:
                    log.warning('Unknown Torch backend')
                for device in [torch.cuda.device(i) for i in range(torch.cuda.device_count())]:
                    log.info(f'Torch detected GPU: {torch.cuda.get_device_name(device)} VRAM {round(torch.cuda.get_device_properties(device).total_memory / 1024 / 1024)} Arch {torch.cuda.get_device_capability(device)} Cores {torch.cuda.get_device_properties(device).multi_processor_count}')
            else:
                try:
                    if args.use_directml and allow_directml:
                        import torch_directml # pylint: disable=import-error
                        version = pkg_resources.get_distribution("torch-directml")
                        log.info(f'Torch backend: DirectML ({version})')
                        for i in range(0, torch_directml.device_count()):
                            log.info(f'Torch detected GPU: {torch_directml.device_name(i)}')
                except Exception:
                    log.warning("Torch reports CUDA not available")
        except Exception as e:
            log.error(f'Could not load torch: {e}')
            if not args.ignore:
                sys.exit(1)
    if args.version:
        return
    try:
        if 'xformers' in xformers_package:
            install(f'--no-deps {xformers_package}', ignore=True)
        elif not args.experimental:
            x = pkg_resources.working_set.by_key.get('xformers', None)
            if x is not None:
                log.warning(f'Not used, uninstalling: {x}')
                pip('uninstall xformers --yes --quiet', ignore=True, quiet=True)
    except Exception as e:
        log.debug(f'Cannot install xformers package: {e}')
    if opts.get('cuda_compile_backend', '') == 'hidet':
        install('hidet', 'hidet')
    if args.use_openvino or opts.get('cuda_compile_backend', '') == 'openvino_fx':
        install('openvino==2023.1.0.dev20230811', 'openvino')
        os.environ.setdefault('PYTORCH_TRACING_MODE', 'TORCHFX')
    if args.profile:
        print_profile(pr, 'Torch')


# check modified files
def check_modified_files():
    if args.quick:
        return
    if args.skip_git:
        return
    try:
        res = git('status --porcelain')
        files = [x[2:].strip() for x in res.split('\n')]
        files = [x for x in files if len(x) > 0 and (not x.startswith('extensions')) and (not x.startswith('wiki')) and (not x.endswith('.json')) and ('.log' not in x)]
        if len(files) > 0:
            log.warning(f'Modified files: {files}')
    except Exception:
        pass


# install required packages
def install_packages():
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    log.info('Verifying packages')
    # gfpgan_package = os.environ.get('GFPGAN_PACKAGE', "git+https://github.com/TencentARC/GFPGAN.git@8d2447a2d918f8eba5a4a01463fd48e45126a379")
    # openclip_package = os.environ.get('OPENCLIP_PACKAGE', "git+https://github.com/mlfoundations/open_clip.git@bb6e834e9c70d9c27d0dc3ecedeebeaeb1ffad6b")
    # install(gfpgan_package, 'gfpgan')
    # install(openclip_package, 'open-clip-torch')
    clip_package = os.environ.get('CLIP_PACKAGE', "git+https://github.com/openai/CLIP.git")
    install(clip_package, 'clip')
    invisiblewatermark_package = os.environ.get('INVISIBLEWATERMARK_PACKAGE', "git+https://github.com/patrickvonplaten/invisible-watermark.git@remove_onnxruntime_depedency")
    install(invisiblewatermark_package, 'invisible-watermark')
    install('onnxruntime==1.15.1', 'onnxruntime', ignore=True)
    install('pi-heif', 'pi_heif', ignore=True)
    tensorflow_package = os.environ.get('TENSORFLOW_PACKAGE', 'tensorflow==2.13.0')
    install(tensorflow_package, 'tensorflow', ignore=True)
    install('git+https://github.com/google-research/torchsde', 'torchsde', ignore=True)
    bitsandbytes_package = os.environ.get('BITSANDBYTES_PACKAGE', None)
    if bitsandbytes_package is not None:
        install(bitsandbytes_package, 'bitsandbytes', ignore=True)
    elif not args.experimental:
        bitsandbytes_package = pkg_resources.working_set.by_key.get('bitsandbytes', None)
        if bitsandbytes_package is not None:
            log.warning(f'Not used, uninstalling: {bitsandbytes_package}')
            pip('uninstall bitsandbytes --yes --quiet', ignore=True, quiet=True)
    if args.profile:
        print_profile(pr, 'Packages')


# clone required repositories
def install_repositories():
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    def d(name):
        return os.path.join(os.path.dirname(__file__), 'repositories', name)
    log.info('Verifying repositories')
    os.makedirs(os.path.join(os.path.dirname(__file__), 'repositories'), exist_ok=True)
    stable_diffusion_repo = os.environ.get('STABLE_DIFFUSION_REPO', "https://github.com/Stability-AI/stablediffusion.git")
    # stable_diffusion_commit = os.environ.get('STABLE_DIFFUSION_COMMIT_HASH', "cf1d67a6fd5ea1aa600c4df58e5b47da45f6bdbf")
    stable_diffusion_commit = os.environ.get('STABLE_DIFFUSION_COMMIT_HASH', None)
    clone(stable_diffusion_repo, d('stable-diffusion-stability-ai'), stable_diffusion_commit)
    taming_transformers_repo = os.environ.get('TAMING_TRANSFORMERS_REPO', "https://github.com/CompVis/taming-transformers.git")
    # taming_transformers_commit = os.environ.get('TAMING_TRANSFORMERS_COMMIT_HASH', "3ba01b241669f5ade541ce990f7650a3b8f65318")
    taming_transformers_commit = os.environ.get('TAMING_TRANSFORMERS_COMMIT_HASH', None)
    clone(taming_transformers_repo, d('taming-transformers'), taming_transformers_commit)
    k_diffusion_repo = os.environ.get('K_DIFFUSION_REPO', 'https://github.com/crowsonkb/k-diffusion.git')
    # k_diffusion_commit = os.environ.get('K_DIFFUSION_COMMIT_HASH', "b43db16749d51055f813255eea2fdf1def801919")
    k_diffusion_commit = os.environ.get('K_DIFFUSION_COMMIT_HASH', 'ab527a9')
    clone(k_diffusion_repo, d('k-diffusion'), k_diffusion_commit)
    codeformer_repo = os.environ.get('CODEFORMER_REPO', 'https://github.com/sczhou/CodeFormer.git')
    # codeformer_commit = os.environ.get('CODEFORMER_COMMIT_HASH', "c5b4593074ba6214284d6acd5f1719b6c5d739af")
    codeformer_commit = os.environ.get('CODEFORMER_COMMIT_HASH', "7a584fd")
    clone(codeformer_repo, d('CodeFormer'), codeformer_commit)
    blip_repo = os.environ.get('BLIP_REPO', 'https://github.com/salesforce/BLIP.git')
    # blip_commit = os.environ.get('BLIP_COMMIT_HASH', "48211a1594f1321b00f14c9f7a5b4813144b2fb9")
    blip_commit = os.environ.get('BLIP_COMMIT_HASH', None)
    clone(blip_repo, d('BLIP'), blip_commit)
    if args.profile:
        print_profile(pr, 'Repositories')


# run extension installer
def run_extension_installer(folder):
    path_installer = os.path.realpath(os.path.join(folder, "install.py"))
    if not os.path.isfile(path_installer):
        return
    try:
        log.debug(f"Running extension installer: {path_installer}")
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.abspath(".")
        result = subprocess.run(f'"{sys.executable}" "{path_installer}"', shell=True, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=folder)
        if result.returncode != 0:
            global errors # pylint: disable=global-statement
            errors += 1
            txt = result.stdout.decode(encoding="utf8", errors="ignore")
            if len(result.stderr) > 0:
                txt = txt + '\n' + result.stderr.decode(encoding="utf8", errors="ignore")
            log.error(f'Error running extension installer: {path_installer}')
            log.debug(txt)
    except Exception as e:
        log.error(f'Exception running extension installer: {e}')

# get list of all enabled extensions
def list_extensions_folder(folder, quiet=False):
    name = os.path.basename(folder)
    disabled_extensions_all = opts.get('disable_all_extensions', 'none')
    if disabled_extensions_all != 'none':
        return []
    disabled_extensions = opts.get('disabled_extensions', [])
    enabled_extensions = [x for x in os.listdir(folder) if x not in disabled_extensions and not x.startswith('.')]
    if not quiet:
        log.info(f'Enabled {name}: {enabled_extensions}')
    return enabled_extensions


# run installer for each installed and enabled extension and optionally update them
def install_extensions():
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    pkg_resources._initialize_master_working_set() # pylint: disable=protected-access
    pkgs = [f'{p.project_name}=={p._version}' for p in pkg_resources.working_set] # pylint: disable=protected-access,not-an-iterable
    log.debug(f'Installed packages: {len(pkgs)}')
    from modules.paths_internal import extensions_builtin_dir, extensions_dir
    extensions_duplicates = []
    extensions_enabled = []
    extension_folders = [extensions_builtin_dir] if args.safe else [extensions_builtin_dir, extensions_dir]
    for folder in extension_folders:
        if not os.path.isdir(folder):
            continue
        extensions = list_extensions_folder(folder, quiet=True)
        log.debug(f'Extensions all: {extensions}')
        for ext in extensions:
            if ext in extensions_enabled:
                extensions_duplicates.append(ext)
                continue
            extensions_enabled.append(ext)
            if args.upgrade:
                try:
                    update(os.path.join(folder, ext))
                except Exception:
                    log.error(f'Error updating extension: {os.path.join(folder, ext)}')
            if not args.skip_extensions:
                run_extension_installer(os.path.join(folder, ext))
            pkg_resources._initialize_master_working_set() # pylint: disable=protected-access
            updated = [f'{p.project_name}=={p._version}' for p in pkg_resources.working_set] # pylint: disable=protected-access,not-an-iterable
            diff = [x for x in updated if x not in pkgs]
            pkgs = updated
            if len(diff) > 0:
                log.info(f'Extension installed packages: {ext} {diff}')
    log.info(f'Extensions enabled: {extensions_enabled}')
    if len(extensions_duplicates) > 0:
        log.warning(f'Extensions duplicates: {extensions_duplicates}')
    if args.profile:
        print_profile(pr, 'Extensions')


# initialize and optionally update submodules
def install_submodules():
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    log.info('Verifying submodules')
    txt = git('submodule')
    # log.debug(f'Submodules list: {txt}')
    if 'no submodule mapping found' in txt:
        log.warning('Attempting repository recover')
        git('add .')
        git('stash')
        git('merge --abort', folder=None, ignore=True)
        git('fetch --all')
        git('reset --hard origin/master')
        git('checkout master')
        txt = git('submodule')
        log.info('Continuing setup')
    git('submodule --quiet update --init --recursive')
    git('submodule --quiet sync --recursive')
    submodules = txt.splitlines()
    for submodule in submodules:
        try:
            name = submodule.split()[1].strip()
            if args.upgrade:
                update(name)
            else:
                branch(name)
        except Exception:
            log.error(f'Error updating submodule: {submodule}')
    if args.profile:
        print_profile(pr, 'Submodule')


def ensure_base_requirements():
    try:
        import rich # pylint: disable=unused-import
    except ImportError:
        install('rich', 'rich')


def install_requirements():
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    if args.skip_requirements and not args.requirements:
        return
    log.info('Verifying requirements')
    with open('requirements.txt', 'r', encoding='utf8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip() != '' and not line.startswith('#') and line is not None]
        for line in lines:
            install(line)
    if args.profile:
        print_profile(pr, 'Requirements')


# set environment variables controling the behavior of various libraries
def set_environment():
    log.debug('Setting environment tuning')
    os.environ.setdefault('USE_TORCH', '1')
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
    os.environ.setdefault('ACCELERATE', 'True')
    os.environ.setdefault('FORCE_CUDA', '1')
    os.environ.setdefault('ATTN_PRECISION', 'fp16')
    os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'garbage_collection_threshold:0.8,max_split_size_mb:512')
    os.environ.setdefault('CUDA_LAUNCH_BLOCKING', '0')
    os.environ.setdefault('CUDA_CACHE_DISABLE', '0')
    os.environ.setdefault('CUDA_AUTO_BOOST', '1')
    os.environ.setdefault('CUDA_MODULE_LOADING', 'LAZY')
    os.environ.setdefault('CUDA_DEVICE_DEFAULT_PERSISTING_L2_CACHE_PERCENTAGE_LIMIT', '0')
    os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
    os.environ.setdefault('SAFETENSORS_FAST_GPU', '1')
    os.environ.setdefault('NUMEXPR_MAX_THREADS', '16')
    os.environ.setdefault('PYTHONHTTPSVERIFY', '0')
    os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
    os.environ.setdefault('HF_HUB_DISABLE_EXPERIMENTAL_WARNING', '1')
    os.environ.setdefault('UVICORN_TIMEOUT_KEEP_ALIVE', '60')
    if sys.platform == 'darwin':
        os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')


def check_extensions():
    newest_all = os.path.getmtime('requirements.txt')
    from modules.paths_internal import extensions_builtin_dir, extensions_dir
    extension_folders = [extensions_builtin_dir] if args.safe else [extensions_builtin_dir, extensions_dir]
    disabled_extensions_all = opts.get('disable_all_extensions', 'none')
    if disabled_extensions_all != 'none':
        log.info(f'Disabled extensions: {disabled_extensions_all}')
    else:
        log.info(f'Disabled extensions: {opts.get("disabled_extensions", [])}')
    for folder in extension_folders:
        if not os.path.isdir(folder):
            continue
        extensions = list_extensions_folder(folder)
        for ext in extensions:
            newest = 0
            extension_dir = os.path.join(folder, ext)
            if not os.path.isdir(extension_dir):
                log.debug(f'Extension listed as installed but folder missing: {extension_dir}')
                continue
            for f in os.listdir(extension_dir):
                if '.json' in f or '.csv' in f or '__pycache__' in f:
                    continue
                ts = os.path.getmtime(os.path.join(extension_dir, f))
                newest = max(newest, ts)
            newest_all = max(newest_all, newest)
            # log.debug(f'Extension version: {time.ctime(newest)} {folder}{os.pathsep}{ext}')
    return round(newest_all)


# check version of the main repo and optionally upgrade it
def check_version(offline=False, reset=True): # pylint: disable=unused-argument
    if not os.path.exists('.git'):
        log.error('Not a git repository')
        if not args.ignore:
            sys.exit(1)
    ver = git('log -1 --pretty=format:"%h %ad"')
    log.info(f'Version: {ver}')
    if args.version or args.skip_git:
        return
    commit = git('rev-parse HEAD')
    global git_commit # pylint: disable=global-statement
    git_commit = commit[:7]
    if args.quick:
        return
    try:
        import requests
    except ImportError:
        return
    commits = None
    try:
        commits = requests.get('https://api.github.com/repos/vladmandic/automatic/branches/master', timeout=10).json()
        if commits['commit']['sha'] != commit:
            if args.upgrade:
                global quick_allowed # pylint: disable=global-statement
                quick_allowed = False
                log.info('Updating main repository')
                try:
                    git('add .')
                    git('stash')
                    update('.', current_branch=True)
                    # git('git stash pop')
                    ver = git('log -1 --pretty=format:"%h %ad"')
                    log.info(f'Upgraded to version: {ver}')
                except Exception:
                    if not reset:
                        log.error('Error during repository upgrade')
                    else:
                        log.warning('Retrying repository upgrade...')
                        git_reset()
                        check_version(offline=offline, reset=False)
            else:
                log.info(f'Latest published version: {commits["commit"]["sha"]} {commits["commit"]["commit"]["author"]["date"]}')
    except Exception as e:
        log.error(f'Failed to check version: {e} {commits}')


def update_wiki():
    if args.upgrade:
        log.info('Updating Wiki')
        try:
            update(os.path.join(os.path.dirname(__file__), "wiki"))
        except Exception:
            log.error('Error updating wiki')


# check if we can run setup in quick mode
def check_timestamp():
    if not quick_allowed or not os.path.isfile(log_file):
        return False
    if args.quick:
        return True
    if args.skip_git:
        return True
    ok = True
    setup_time = -1
    with open(log_file, 'r', encoding='utf8') as f:
        lines = f.readlines()
        for line in lines:
            if 'Setup complete without errors' in line:
                setup_time = int(line.split(' ')[-1])
    try:
        version_time = int(git('log -1 --pretty=format:"%at"'))
    except Exception as e:
        log.error(f'Error getting local repository version: {e}')
        if not args.ignore:
            sys.exit(1)
    log.debug(f'Repository update time: {time.ctime(int(version_time))}')
    if setup_time == -1:
        return False
    log.debug(f'Previous setup time: {time.ctime(setup_time)}')
    if setup_time < version_time:
        ok = False
    extension_time = check_extensions()
    log.debug(f'Latest extensions time: {time.ctime(extension_time)}')
    if setup_time < extension_time:
        ok = False
    log.debug(f'Timestamps: version:{version_time} setup:{setup_time} extension:{extension_time}')
    if args.reinstall:
        ok = False
    return ok


def add_args(parser):
    group = parser.add_argument_group('Setup options')
    group.add_argument('--debug', default = False, action='store_true', help = "Run installer with debug logging, default: %(default)s")
    group.add_argument('--reset', default = False, action='store_true', help = "Reset main repository to latest version, default: %(default)s")
    group.add_argument('--upgrade', default = False, action='store_true', help = "Upgrade main repository to latest version, default: %(default)s")
    group.add_argument('--requirements', default = False, action='store_true', help = "Force re-check of requirements, default: %(default)s")
    group.add_argument('--quick', default = False, action='store_true', help = "Run with startup sequence only, default: %(default)s")
    group.add_argument('--use-directml', default = False, action='store_true', help = "Use DirectML if no compatible GPU is detected, default: %(default)s")
    group.add_argument("--use-openvino", default = False, action='store_true', help="Use Intel OpenVINO backend, default: %(default)s")
    group.add_argument("--use-ipex", default = False, action='store_true', help="Force use Intel OneAPI XPU backend, default: %(default)s")
    group.add_argument("--use-cuda", default=False, action='store_true', help="Force use nVidia CUDA backend, default: %(default)s")
    group.add_argument("--use-rocm", default=False, action='store_true', help="Force use AMD ROCm backend, default: %(default)s")
    group.add_argument('--skip-requirements', default = False, action='store_true', help = "Skips checking and installing requirements, default: %(default)s")
    group.add_argument('--skip-extensions', default = False, action='store_true', help = "Skips running individual extension installers, default: %(default)s")
    group.add_argument('--skip-git', default = False, action='store_true', help = "Skips running all GIT operations, default: %(default)s")
    group.add_argument('--skip-torch', default = False, action='store_true', help = "Skips running Torch checks, default: %(default)s")
    group.add_argument('--experimental', default = False, action='store_true', help = "Allow unsupported versions of libraries, default: %(default)s")
    group.add_argument('--reinstall', default = False, action='store_true', help = "Force reinstallation of all requirements, default: %(default)s")
    group.add_argument('--test', default = False, action='store_true', help = "Run test only and exit")
    group.add_argument('--version', default = False, action='store_true', help = "Print version information")
    group.add_argument('--ignore', default = False, action='store_true', help = "Ignore any errors and attempt to continue")
    group.add_argument('--safe', default = False, action='store_true', help = "Run in safe mode with no user extensions")


def parse_args(parser):
    # command line args
    global args # pylint: disable=global-statement
    args = parser.parse_args()
    return args


def extensions_preload(parser):
    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
    if args.safe:
        log.info('Running in safe mode without user extensions')
    try:
        from modules.script_loading import preload_extensions
        from modules.paths_internal import extensions_builtin_dir, extensions_dir
        extension_folders = [extensions_builtin_dir] if args.safe else [extensions_builtin_dir, extensions_dir]
        for ext_dir in extension_folders:
            t0 = time.time()
            preload_extensions(ext_dir, parser)
            t1 = time.time()
            log.info(f'Extension preload: {round(t1 - t0, 1)}s {ext_dir}')
    except Exception:
        log.error('Error running extension preloading')
    if args.profile:
        print_profile(pr, 'Preload')


def git_reset():
    log.warning('Running GIT reset')
    global quick_allowed # pylint: disable=global-statement
    quick_allowed = False
    git('merge --abort')
    git('fetch --all')
    git('reset --hard origin/master')
    git('checkout master')
    log.info('GIT reset complete')


def read_options():
    global opts # pylint: disable=global-statement
    if os.path.isfile(args.config):
        with open(args.config, "r", encoding="utf8") as file:
            try:
                opts = json.load(file)
                if type(opts) is str:
                    opts = json.loads(opts)
            except Exception as e:
                log.error(f'Error reading options file: {file} {e}')
