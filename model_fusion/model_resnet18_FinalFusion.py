import os
# os.environ['CUDA_VISIBLE_DEVICES'] =  '4'
from utils import *
import torchvision.models as tvm
from torchvision.models.resnet import BasicBlock
import torch.nn as nn
import torch
import torch.nn.functional as F
import numpy as np

BatchNorm2d = nn.BatchNorm2d

from model.model_resnet18 import Net


###########################################################################################3
class FusionNet(nn.Module):
    def load_pretrain(self, pretrain_file):
        #raise NotImplementedError
        pretrain_state_dict = torch.load(pretrain_file)
        state_dict = self.state_dict()
        keys = list(state_dict.keys())
        for key in keys:
            state_dict[key] = pretrain_state_dict[key]

        self.load_state_dict(state_dict)
        print('')


    def __init__(self, num_class=2):
        super(FusionNet,self).__init__()

        self.color_moudle  = Net(num_class=num_class,is_first_bn=True)

        self.depth_moudle = Net(num_class=num_class,is_first_bn=True)

        self.ir_moudle = Net(num_class=num_class,is_first_bn=True)

        self.color_moudle.load_pretrain(r'/data1/shentao/Projects/CVPR19FaceAntiSpoofing/models/'
                                        r'tmp_color_t1_60epoch/checkpoint/min_acer_model.pth')
        self.depth_moudle.load_pretrain(r'/data1/shentao/Projects/CVPR19FaceAntiSpoofing/models/'
                                        r'tmp_depth_t1_60epoch/checkpoint/min_acer_model.pth')
        self.ir_moudle.load_pretrain(r'/data1/shentao/Projects/CVPR19FaceAntiSpoofing/models/'
                                        r'tmp_ir_t1_60epoch/checkpoint/min_acer_model.pth')

        # for param in self.color_moudle.parameters():
        #     param.detach_()
        # for param in self.depth_moudle.parameters():
        #     param.detach_()
        # for param in self.ir_moudle.parameters():
        #     param.detach_()

        self.fc = nn.Sequential(nn.Dropout(0.5),
                                nn.Linear(512*3, 512),
                                nn.ReLU(inplace=True),
                                nn.Dropout(0.5),
                                nn.Linear(512, num_class))

    def _make_layer(self, block, inplanes, planes, blocks, stride=1):
        downsample = None
        if stride != 1 :
            downsample = nn.Sequential(
                nn.Conv2d(inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),)

        layers = []
        layers.append(block(inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)


    def forward(self, x):
        batch_size,C,H,W = x.shape

        color = x[:, 0:3,:,:]
        # color = torch.cat([color,color,color],1)
        depth = x[:, 3:6,:,:]
        # depth = torch.cat([depth,depth,depth],1)
        ir = x[:, 6:9,:,:]
        # ir = torch.cat([ir,ir,ir],1)

        _,_,color_feas = self.color_moudle.forward(color)
        _,_,depth_feas = self.depth_moudle.forward(depth)
        _,_,ir_feas = self.ir_moudle.forward(ir)

        fea = torch.cat([color_feas, depth_feas, ir_feas], dim=1)
        x = self.fc(fea)
        return x,_,_

    def set_mode(self, mode, is_freeze_bn=False ):
        self.mode = mode
        if mode in ['eval', 'valid', 'test']:
            self.eval()
        elif mode in ['backup']:
            self.train()
            if is_freeze_bn==True: ##freeze
                for m in self.modules():
                    if isinstance(m, BatchNorm2d):
                        m.eval()
                        m.weight.requires_grad = False
                        m.bias.requires_grad   = False

### run ##############################################################################
def run_check_net():
    batch_size = 32
    C,H,W = 3, 128, 128
    num_class = 2

    input = np.random.uniform(0,1, (batch_size,C,H,W)).astype(np.float32)
    truth = np.random.choice (num_class,   batch_size).astype(np.float32)

    #------------
    input = torch.from_numpy(input).float().cuda()
    truth = torch.from_numpy(truth).long().cuda()

    input = to_var(input)
    truth = to_var(truth)

    #---
    criterion = softmax_cross_entropy_criterion
    net = Net(num_class).cuda()
    net.set_mode('backup')
    print(net)
    ## exit(0)
    # net.load_pretrain('/media/st/SSD02/Projects/Kaggle_draw/models/resnet34-fold0/checkpoint/00006000_model.pth')

    logit = net.forward(input)
    loss  = criterion(logit, truth)

########################################################################################
if __name__ == '__main__':
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = '4,5,6,7'  # '3,2,1,0'
    print( '%s: calling main function ... ' % os.path.basename(__file__))
    run_check_net()
    print( 'sucessful!')