import math
import random

import gradio as gr
import modules.scripts as scripts
from modules import deepbooru, images, processing, shared
from modules.processing import Processed
from modules.shared import opts, state

from PIL import Image
import copy

global pixmap
global xn


class Script(scripts.Script):

    def title(self):
        return "Plasma Noise"

    def show(self, is_img2img):
        if not is_img2img:
            return scripts.AlwaysVisible
        return False

    def ui(self, is_img2img):
        with gr.Accordion('Plasma Noise', open=False):
            enabled = gr.Checkbox(label="Enabled", default=False)
            turbulence = gr.Slider(minimum=0.05, maximum=10.0, step=0.05, label='Turbulence', value=2.75, elem_id=self.elem_id("turbulence"))
            denoising = gr.Slider(minimum=0.0, maximum=1.0, step=0.01, label='Denoising strength', value=0.9, elem_id=self.elem_id("denoising"))
            noise_mult = gr.Slider(minimum=0.0, maximum=1.0, step=0.01, label='Noise multiplier', value=1.0, elem_id=self.elem_id("noise_mult"))
            val_min = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Value Min", elem_id=self.elem_id("val_min"))
            val_max = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Value Max", elem_id=self.elem_id("val_max"))
            red_min = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Red Min", elem_id=self.elem_id("red_min"))
            red_max = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Red Max", elem_id=self.elem_id("red_max"))
            grn_min = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Green Min", elem_id=self.elem_id("grn_min"))
            grn_max = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Green Max", elem_id=self.elem_id("grn_max"))
            blu_min = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Blue Min", elem_id=self.elem_id("blu_min"))
            blu_max = gr.Slider(minimum=-1, maximum=255, step=1, value=-1, label="Blue Max", elem_id=self.elem_id("blu_max"))

        return [enabled, turbulence, denoising, noise_mult, val_min, val_max, red_min, red_max, grn_min, grn_max, blu_min, blu_max]

    def process(self, p, enabled, turbulence, denoising, noise_mult, val_min, val_max, red_min, red_max, grn_min, grn_max, blu_min, blu_max):
        if not enabled:
            return None
            
        global pixmap
        global xn
        xn = 0
        # image size
        p.__class__ = processing.StableDiffusionProcessingImg2Img
        p.mask = None
        p.image_mask = None
        p.latent_mask = None
        p.resize_mode = None
        p.extra_generation_params["Alt noise type"] = "Plasma"
        p.extra_generation_params["Turbulence"] = turbulence
        p.extra_generation_params["Alt denoising strength"] = denoising
        p.extra_generation_params["Value Min"] = val_min
        p.extra_generation_params["Value Max"] = val_max
        p.extra_generation_params["Red Min"] = red_min
        p.extra_generation_params["Red Max"] = red_max
        p.extra_generation_params["Green Min"] = grn_min
        p.extra_generation_params["Green Max"] = grn_max
        p.extra_generation_params["Blue Min"] = blu_min
        p.extra_generation_params["Blue Max"] = blu_max
        p.initial_noise_multiplier = noise_mult
        p.denoising_strength = denoising
        
        w = p.width
        h = p.height
        processing.fix_seed(p)
        random.seed(p.seed)
        aw = copy.deepcopy(w)
        ah = copy.deepcopy(h)
        image = Image.new("RGB", (aw, ah))
        if w >= h:
            h = w
        else:
            w = h

        # Clamp per channel and globally
        clamp_v_min = val_min
        clamp_v_max = val_max
        clamp_r_min = red_min
        clamp_r_max = red_max
        clamp_g_min = grn_min
        clamp_g_max = grn_max
        clamp_b_min = blu_min
        clamp_b_max = blu_max

        # Handle value clamps
        lv = 0
        mv = 0
        if clamp_v_min == -1:
            lv = 0
        else:
            lv = clamp_v_min

        if clamp_v_max == -1:
            mv = 255
        else:
            mv = clamp_v_max

        lr = 0
        mr = 0
        if clamp_r_min == -1:
            lr = lv
        else:
            lr = clamp_r_min

        if clamp_r_max == -1:
            mr = mv
        else:
            mr = clamp_r_max

        lg = 0
        mg = 0
        if clamp_g_min == -1:
            lg = lv
        else:
            lg = clamp_g_min

        if clamp_g_max == -1:
            mg = mv
        else:
            mg = clamp_g_max

        lb = 0
        mb = 0
        if clamp_b_min == -1:
            lb = lv
        else:
            lb = clamp_b_min

        if clamp_b_max == -1:
            mb = mv
        else:
            mb = clamp_b_max

        roughness = turbulence

        def adjust(xa, ya, x, y, xb, yb):
            global pixmap
            if (pixmap[x][y] == 0):
                d = math.fabs(xa - xb) + math.fabs(ya - yb)
                v = (pixmap[xa][ya] + pixmap[xb][yb]) / 2.0 + (random.random() - 0.555) * d * roughness
                c = int(math.fabs(v + (random.random() - 0.5) * 96))
                if c < 0:
                    c = 0
                elif c > 255:
                    c = 255
                pixmap[x][y] = c

        def subdivide(x1, y1, x2, y2):
            global pixmap
            if (not ((x2 - x1 < 2.0) and (y2 - y1 < 2.0))):
                x = int((x1 + x2) / 2.0)
                y = int((y1 + y2) / 2.0)
                adjust(x1, y1, x, y1, x2, y1)
                adjust(x2, y1, x2, y, x2, y2)
                adjust(x1, y2, x, y2, x2, y2)
                adjust(x1, y1, x1, y, x1, y2)
                if (pixmap[x][y] == 0):
                    v = int((pixmap[x1][y1] + pixmap[x2][y1] + pixmap[x2][y2] + pixmap[x1][y2]) / 4.0)
                    pixmap[x][y] = v

                subdivide(x1, y1, x, y)
                subdivide(x, y1, x2, y)
                subdivide(x, y, x2, y2)
                subdivide(x1, y, x, y2)

        pixmap = [[0 for i in range(h)] for j in range(w)]
        pixmap[0][0] = int(random.random() * 255)
        pixmap[w - 1][0] = int(random.random() * 255)
        pixmap[w - 1][h - 1] = int(random.random() * 255)
        pixmap[0][h - 1] = int(random.random() * 255)
        subdivide(0, 0, w - 1, h - 1)
        r = copy.deepcopy(pixmap)

        pixmap = [[0 for i in range(h)] for j in range(w)]
        pixmap[0][0] = int(random.random() * 255)
        pixmap[w - 1][0] = int(random.random() * 255)
        pixmap[w - 1][h - 1] = int(random.random() * 255)
        pixmap[0][h - 1] = int(random.random() * 255)
        subdivide(0, 0, w - 1, h - 1)
        g = copy.deepcopy(pixmap)

        pixmap = [[0 for i in range(h)] for j in range(w)]
        pixmap[0][0] = int(random.random() * 255)
        pixmap[w - 1][0] = int(random.random() * 255)
        pixmap[w - 1][h - 1] = int(random.random() * 255)
        pixmap[0][h - 1] = int(random.random() * 255)
        subdivide(0, 0, w - 1, h - 1)
        b = copy.deepcopy(pixmap)

        for y in range(ah):
            for x in range(aw):
                nr = random.randint(lr, mr)
                ng = random.randint(lg, mg)
                nb = random.randint(lb, mb)
                image.putpixel((x,y), (nr, ng, nb))

        p.init_images = [image]

