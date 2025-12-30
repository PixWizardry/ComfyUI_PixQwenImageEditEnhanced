import torch
import math
import comfy.utils
import node_helpers

DEFAULT_SYSTEM_INSTRUCTION = "Describe the key features of the input image (color, shape, size, texture, objects, background), then explain how the user's text instruction should alter or modify the image. Generate a new image that meets the user's requirements while maintaining consistency with the original input where appropriate."

class PixQwenImageEditEnhanced:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "clip": ("CLIP",),
                "USER_PROMPT": ("STRING", {
                    "multiline": True, 
                    "dynamicPrompts": True, 
                    "placeholder": "Describe your request here (e.g. 'Add a dragon to the sky')"
                }),
                "SYSTEM_INSTRUCTION": ("STRING", {
                    "multiline": True, 
                    "default": DEFAULT_SYSTEM_INSTRUCTION, 
                }),
                # NEW: Assistant Priming
                "ASSISTANT_PRIMING": ("STRING", {
                    "multiline": True, 
                    "default": "", 
                    "placeholder": "Optional: Start the AI's response (e.g. 'A high-quality cinematic photo of...')"
                }),
            },
            "optional": {
                "vae": ("VAE",),
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("CONDITIONING", "STRING", "STRING")
    RETURN_NAMES = ("conditioning", "token_log", "final_prompt")
    FUNCTION = "encode"
    CATEGORY = "advanced/conditioning"
    DESCRIPTION = "Enhanced Qwen Image Edit node with Assistant Priming."

    def encode(self, clip, USER_PROMPT, SYSTEM_INSTRUCTION, ASSISTANT_PRIMING, unique_id=None, vae=None, image1=None, image2=None, image3=None, image4=None, image5=None):
        ref_latents = []
        images = [image1, image2, image3, image4, image5]
        images_vl = []
        
        # Updated Template to include the Priming text after the assistant tag
        llama_template_structure = f"<|im_start|>system\n{SYSTEM_INSTRUCTION}<|im_end|>\n<|im_start|>user\n{{}}<|im_end|>\n<|im_start|>assistant\n{ASSISTANT_PRIMING}"
        
        image_prompt = ""
        total_vision_tokens = 0
        token_report_str = ""

        for i, image in enumerate(images):
            if image is not None and image.numel() > 0:
                samples = image.movedim(-1, 1)
                total_vl = int(384 * 384)
                scale_by_vl = math.sqrt(total_vl / (samples.shape[3] * samples.shape[2]))
                width_vl = round(samples.shape[3] * scale_by_vl)
                height_vl = round(samples.shape[2] * scale_by_vl)
                
                tokens_w = width_vl // 14
                tokens_h = height_vl // 14
                img_tokens = tokens_w * tokens_h
                total_vision_tokens += img_tokens
                token_report_str += f"[Img{i+1}:{img_tokens}] "

                s_vl = comfy.utils.common_upscale(samples, width_vl, height_vl, "area", "disabled")
                images_vl.append(s_vl.movedim(1, -1))

                if vae is not None:
                    total_vae = int(1024 * 1024)
                    scale_by_vae = math.sqrt(total_vae / (samples.shape[3] * samples.shape[2]))
                    width_vae = round(samples.shape[3] * scale_by_vae / 8.0) * 8
                    height_vae = round(samples.shape[2] * scale_by_vae / 8.0) * 8
                    s_vae = comfy.utils.common_upscale(samples, width_vae, height_vae, "area", "disabled")
                    ref_latents.append(vae.encode(s_vae.movedim(1, -1)[:, :, :, :3]))

                image_prompt += "Picture {}: <|vision_start|><|image_pad|><|vision_end|>".format(i + 1)

        combined_content = image_prompt + USER_PROMPT
        
        # This is for your 'final_prompt' output display
        final_prompt_string = llama_template_structure.format(combined_content)

        # Tokenize with the new structure
        tokens = clip.tokenize(combined_content, images=images_vl, llama_template=llama_template_structure)
        
        text_token_count = 0
        if "l" in tokens:
            text_token_count = len(tokens["l"][0])
        elif "g" in tokens:
            text_token_count = len(tokens["g"][0])
        else:
            first_key = list(tokens.keys())[0]
            text_token_count = len(tokens[first_key][0])

        grand_total = total_vision_tokens + text_token_count
        conditioning = clip.encode_from_tokens_scheduled(tokens)

        if len(ref_latents) > 0:
            conditioning = node_helpers.conditioning_set_values(conditioning, {"reference_latents": ref_latents}, append=True)

        if grand_total > 0:
            final_ui_text = f"Total: {grand_total} (Vis: {total_vision_tokens} + Txt: {text_token_count}) | {token_report_str}"
        else:
            final_ui_text = "No valid inputs detected."

        return {
            "ui": {"text": [final_ui_text]},
            "result": (conditioning, final_ui_text, final_prompt_string)
        }

NODE_CLASS_MAPPINGS = {"PixQwenImageEditEnhanced": PixQwenImageEditEnhanced}
NODE_DISPLAY_NAME_MAPPINGS = {"PixQwenImageEditEnhanced": "🐋 Pix Qwen Image Edit (5 Images)"}