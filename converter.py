# Copyright (c) 2022  PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import ast
import astor
import shutil
import collections

from .transformer.import_transformer import ImportTransformer
from .transformer.basic_transformer import BasicTransformer


class Converter:
    def __init__(self, log_dir=None):
        self.torch_api_count = 0
        self.success_api_count = 0
        if log_dir is not None:
            self.log_dir = os.getcwd()+ 'convert.log'
        else:
            self.log_dir = log_dir
        self.log_msg = []
        self.log_info("======================================")
        self.log_info("PyTorch to Paddle Convert Start----->:")
        self.log_info("======================================")
        self.imports_map = collections.defaultdict(lambda: dict())
    
    def run(self, in_dir, out_dir):
        in_dir = os.path.abspath(in_dir)
        out_dir = os.path.abspath(out_dir)
        for name in os.listdir(in_dir):
            old_path = os.path.join(in_dir, name)
            new_path = os.path.join(out_dir, name)
            if os.path.isfile(old_path) and old_path.endswith(".py"):
                self.log_info("Finish convert {} ---> {}".format(old_path, new_path))
                with open(old_path, 'r') as f:
                    code = f.read()
                    root = ast.parse(code)
                self.transfer_from_node(root, old_path)

                code = astor.to_source(root)
                code = self.mark_unsport(code)
                with open(new_path, 'w') as file:
                    file.write(code)
            elif os.path.isdir(old_path):
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                self.run(old_path, new_path)
            elif os.path.isfile(old_path) and old_path.endswith("requirements.txt"):
                self.log_info("Finish convert {} ---> {}".format(old_path, new_path))
                old_file = open(old_path, 'r')
                code = old_file.read()
                code = code.replace('torch', 'paddlepaddle')
                new_file = open(new_path, 'w')
                new_file.write(code)
                old_file.close()
                new_file.close()
            else:
                self.log_info("No need to convert, just Copy {} ---> {}".format(old_path, new_path))
                shutil.copyfile(old_path, new_path)    

        self.log_info("======================================")
        self.log_info("Convert Summary:")
        self.log_info("There is {} Pytorch API in project".format(self.torch_api_count))
        self.log_info("{}  Pytorch API have been converted to Paddle successfully".format(self.success_api_count))
        self.log_info("{}  Pytorch API converted failed, Please refer to "
        "https://www.paddlepaddle.org.cn/documentation/docs/zh/guides/model_convert/pytorch_api_mapping_cn.html#pytorch-1-8-paddle-2-0-api "
        "and modify it by yourself manually!".format(self.torch_api_count-self.success_api_count))
        self.log_info("======================================")
        
        with open(self.log_dir, 'a') as file:
            file.write('\n\n\n\n*************************************************\n\n')
            file.write('\n'.join(self.log_msg))

    def mark_unsport(self, code):
        lines = code.split('\n')
        mark_next_line = False
        for i, line in enumerate(lines):
            if 'torch' in line:
                lines[i] = ">>> " + line
            if 'Tensor Method' in line:
                lines[i] = ">>> " + line
                mark_next_line = True
            else:
                if mark_next_line:
                    lines[i] = ">>> " + line
                    mark_next_line = True

        return '\n'.join(lines)


    def log_info(self, msg, file=None, line=None):
        if file:
            if line:
                msg = "[{}:{}] {}".format(file, line, msg)
            else:
                msg = "[{}] {}".format(file, msg)
        else:
            msg = "{}".format(msg)
        logging.info(msg)
        self.log_msg.append(msg)


    def transfer_from_node(self, root, file):
        transformers = [
            ImportTransformer, # import ast transformer
            BasicTransformer,    # basic api ast transformer
        ]
        for transformer in transformers:
            trans = transformer(root, file, self.imports_map)
            trans.transform()
            self.torch_api_count += trans.torch_api_count
            self.success_api_count += trans.success_api_count
            self.log_msg.append(trans.log_msg)
                