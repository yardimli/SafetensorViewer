import os
import json
import logging
import base64
from safetensors.torch import safe_open
from folder_paths import models_dir
from server import PromptServer
import torch
from PIL import Image
import io
import numpy as np


# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SafetensorViewer')

class SafetensorViewer:
    def __init__(self):
        self.output_dir = models_dir
        
    @classmethod
    def INPUT_TYPES(cls):
        # Scan all folders for safetensor files
        all_safetensors = []
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file.endswith('.safetensors'):
                    # Get path relative to models_dir
                    rel_path = os.path.relpath(os.path.join(root, file), models_dir)
                    all_safetensors.append(rel_path)
        
        return {
            "required": {
                "model_file": (sorted(all_safetensors),),
            },
             "optional": {
                "notes": ("STRING", {"multiline": True, "default": "Enter notes here..."})
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("thumbnail",)
    FUNCTION = "view_safetensor"
    CATEGORY = "utils"
    OUTPUT_NODE = True

    def clean_metadata(self, metadata_str):
        try:
            metadata_dict = json.loads(metadata_str)
            if "modelspec.thumbnail" in metadata_dict:
                metadata_dict["modelspec.thumbnail"] = "[THUMBNAIL DATA REMOVED]"
            return json.dumps(metadata_dict, indent=2)
        except:
            return metadata_str

        
    def view_safetensor(self, model_file, notes):        
        # logger.info(f"Viewing safetensor - File: {model_file} - {notes}")
        
        try:
            file_path = os.path.join(self.output_dir, model_file)
            tensor_info = []
            tensor_info_str = ""
            metadata = "No metadata found"
            unique_prefixes = set()
            thumbnail = torch.zeros((1, 64, 64, 3))

            # logger.info(f"Loading: {file_path}, for analysis")

            with safe_open(file_path, framework="pt") as f:
                metadata = f.metadata()
                if metadata:
                    logger.info("Found metadata")
                    metadata = json.dumps(metadata, indent=2)
                    
                    # Extract and process thumbnail if it exists
                    if isinstance(metadata, str):
                        metadata_dict = json.loads(metadata)
                        thumbnail_data = metadata_dict.get("modelspec.thumbnail")
                        if thumbnail_data and thumbnail_data.startswith("data:image/"):
                            try:
                                # Extract the base64 data
                                base64_data = thumbnail_data.split(',')[1]
                                # Decode base64 to image
                                image_data = base64.b64decode(base64_data)
                                # Open as PIL Image
                                thumbnail = Image.open(io.BytesIO(image_data))
                                # Convert to RGB if necessary
                                if thumbnail.mode != 'RGB':
                                    thumbnail = thumbnail.convert('RGB')
                                # Convert PIL image to tensor format expected by ComfyUI
                                thumbnail = np.array(thumbnail).astype(np.float32) / 255.0
                                thumbnail = torch.from_numpy(thumbnail)[None,]
                                
                                # logger.info("Successfully processed thumbnail")
                            except Exception as e:
                                logger.error(f"Error processing thumbnail: {e}")
                                thumbnail = torch.zeros((1, 64, 64, 3))  # Default empty image


                tensor_names = f.keys()
                logger.info(f"Found {len(tensor_names)} tensors")
                tensor_info.append(f"\nNumber of tensors: {len(tensor_names)}")
            
                # Process tensor names and collect unique prefixes
                for name in tensor_names:
                    parts = name.split('.')
                    if len(parts) >= 2:
                        prefix = '.'.join(parts[:2])
                        unique_prefixes.add(prefix)
            
            # Add the unique prefixes to the beginning of tensor_info
            prefix_list = sorted(list(unique_prefixes))
            tensor_info.insert(1, "\nUnique Prefixes:")
            for prefix in prefix_list:
                tensor_info.insert(2, f"\n- {prefix}")
            
            tensor_info_str = "\n".join(tensor_info)
            metadata = self.clean_metadata(metadata)
            
        except Exception as e:
            logger.error(f"Error reading safetensor file: {e}")
            tensor_info_str = f"Error reading file: {str(e)}"
            metadata = "Error reading metadata"
            thumbnail = torch.zeros((1, 64, 64, 3))  # Default empty image
        
         
        # Send update to frontend
        PromptServer.instance.send_sync("SafetensorViewer.update_files", {
            "node": self.__class__.__name__,
            "model_file": model_file,
            "notes": notes,
            "metadata": metadata,
            "tensor_info": tensor_info
        })
        
        # logger.info(f"Returning safetensor - tensor_info_str: {tensor_info_str}, \n metadata: {metadata}")
        return (thumbnail,)


NODE_CLASS_MAPPINGS = {
    "SafetensorViewer": SafetensorViewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SafetensorViewer": "SafeTensor and Meta Viewer",
}