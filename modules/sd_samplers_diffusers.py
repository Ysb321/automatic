from modules.shared import opts, log
from modules import sd_samplers_common

try:
    from diffusers import (
        DDIMScheduler,
        DDPMScheduler,
        DEISMultistepScheduler,
        DPMSolverMultistepScheduler,
        DPMSolverSinglestepScheduler,
        EulerAncestralDiscreteScheduler,
        EulerDiscreteScheduler,
        HeunDiscreteScheduler,
        KDPM2DiscreteScheduler,
        PNDMScheduler,
        UniPCMultistepScheduler,
        LMSDiscreteScheduler,
        KDPM2AncestralDiscreteScheduler,
    )
except Exception as e:
    import diffusers
    log.error(f'Diffusers import error: version={diffusers.__version__} error: {e}')

config = {
    # beta_start, beta_end are typically per-scheduler, but we don't want them as they should be taken from the model itself as those are values model was trained on
    # prediction_type is ideally set in model as well, but it maybe needed that we do auto-detect of model type in the future
    'All': { 'num_train_timesteps': 1000, 'beta_start': 0.0001, 'beta_end': 0.02, 'beta_schedule': 'linear', 'prediction_type': 'epsilon' },
    'DDIM': { 'clip_sample': True, 'set_alpha_to_one': True, 'steps_offset': 0, 'thresholding': False, 'clip_sample_range': 1.0, 'sample_max_value': 1.0, 'timestep_spacing': 'linspace', 'rescale_betas_zero_snr': False },
    'DDPM': { 'variance_type': "fixed_small", 'clip_sample': True, 'thresholding': False, 'clip_sample_range': 1.0, 'sample_max_value': 1.0, 'timestep_spacing': 'linspace'},
    'DEIS': { 'solver_order': 2, 'thresholding': False, 'sample_max_value': 1.0, 'algorithm_type': "deis", 'solver_type': "logrho", 'lower_order_final': True },
    'DPM 1S': { 'solver_order': 2, 'thresholding': False, 'sample_max_value': 1.0, 'algorithm_type': "dpmsolver++", 'solver_type': "midpoint", 'lower_order_final': True, 'use_karras_sigmas': False },
    'DPM 2M': { 'thresholding': False, 'sample_max_value': 1.0, 'algorithm_type': "dpmsolver++", 'solver_type': "midpoint", 'lower_order_final': True, 'use_karras_sigmas': False },
    'Euler a': { },
    'Euler': { 'interpolation_type': "linear", 'use_karras_sigmas': False },
    'Heun': { 'use_karras_sigmas': False },
    'KDPM2 a': { 'steps_offset': 0 },
    'KDPM2': { 'steps_offset': 0 },
    'LMSD': { 'use_karras_sigmas': False, 'timestep_spacing': 'linspace', 'steps_offset': 0 },
    'PNDM': { 'skip_prk_steps': False, 'set_alpha_to_one': False, 'steps_offset': 0 },
    'UniPC': { 'solver_order': 2, 'thresholding': False, 'sample_max_value': 1.0, 'predict_x0': 'bh2', 'lower_order_final': True },
}

samplers_data_diffusers = [
    sd_samplers_common.SamplerData('Default', None, [], {}),
    sd_samplers_common.SamplerData('UniPC', lambda model: DiffusionSampler('UniPC', UniPCMultistepScheduler, model), [], {}),
    sd_samplers_common.SamplerData('DEIS', lambda model: DiffusionSampler('DEIS', DEISMultistepScheduler, model), [], {}),
    sd_samplers_common.SamplerData('PNDM', lambda model: DiffusionSampler('PNDM', PNDMScheduler, model), [], {}),
    sd_samplers_common.SamplerData('DDPM', lambda model: DiffusionSampler('DDPM', DDPMScheduler, model), [], {}),
    sd_samplers_common.SamplerData('DDIM', lambda model: DiffusionSampler('DDIM', DDIMScheduler, model), [], {}),
    sd_samplers_common.SamplerData('LMSD', lambda model: DiffusionSampler('LMSD', LMSDiscreteScheduler, model), [], {}),
    sd_samplers_common.SamplerData('KDPM2', lambda model: DiffusionSampler('KDPM2', KDPM2DiscreteScheduler, model), [], {}),
    sd_samplers_common.SamplerData('KDPM2 a', lambda model: DiffusionSampler('KDPM2 a', KDPM2AncestralDiscreteScheduler, model), [], {}),
    sd_samplers_common.SamplerData('DPM 1S', lambda model: DiffusionSampler('DPM++ 1S', DPMSolverSinglestepScheduler, model), [], {}),
    sd_samplers_common.SamplerData('DPM 2M', lambda model: DiffusionSampler('DPM++ 2M', DPMSolverMultistepScheduler, model), [], {}),
    sd_samplers_common.SamplerData('Euler', lambda model: DiffusionSampler('Euler', EulerDiscreteScheduler, model), [], {}),
    sd_samplers_common.SamplerData('Euler a', lambda model: DiffusionSampler('Euler a', EulerAncestralDiscreteScheduler, model), [], {}),
    sd_samplers_common.SamplerData('Heun', lambda model: DiffusionSampler('Heun', HeunDiscreteScheduler, model), [], {}),
]

class DiffusionSampler:
    def __init__(self, name, constructor, model, **kwargs):
        if name == 'Default':
            return
        self.name = name
        self.config = {}
        self.config = config['All'].copy() # apply global defaults
        if not hasattr(model, 'scheduler'):
            return
        for key, value in config.get(name, {}).items(): # apply diffusers per-scheduler defaults
            self.config[key] = value
        if hasattr(model.scheduler, 'scheduler_config'): # find model defaults
            orig_config = model.scheduler.scheduler_config
        else:
            orig_config = model.scheduler.config
        for key, value in orig_config.items(): # apply model defaults
            if key in self.config:
                self.config[key] = value
        for key, value in kwargs.items(): # apply user args, if any
            if key in self.config:
                self.config[key] = value
        # finally apply user preferences
        if opts.schedulers_prediction_type != 'default':
            self.config['prediction_type'] = opts.schedulers_prediction_type
        if opts.schedulers_beta_schedule != 'default':
            self.config['beta_schedule'] = opts.schedulers_beta_schedule
        if 'use_karras_sigmas' in self.config:
            self.config['use_karras_sigmas'] = opts.schedulers_use_karras
        if 'thresholding' in self.config:
            self.config['thresholding'] = opts.schedulers_use_thresholding
        if 'lower_order_final' in self.config:
            self.config['lower_order_final'] = opts.schedulers_use_loworder
        if 'solver_order' in self.config:
            self.config['solver_order'] = opts.schedulers_solver_order
        if 'predict_x0' in self.config:
            self.config['predict_x0'] = opts.uni_pc_variant
        if name == 'DPM 2M':
            self.config['algorithm_type'] = opts.schedulers_dpm_solver
        if 'beta_start' in self.config and opts.schedulers_beta_start > 0:
            self.config['beta_start'] = opts.schedulers_beta_start
        if 'beta_end' in self.config and opts.schedulers_beta_end > 0:
            self.config['beta_end'] = opts.schedulers_beta_end
        self.sampler = constructor(**self.config)
        self.sampler.name = name
