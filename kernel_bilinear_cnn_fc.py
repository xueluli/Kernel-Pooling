#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fine-tune all layers for bilinear CNN.

Usage:
    CUDA_VISIBLE_DEVICES=0,1,2,3 ./src/bilinear_cnn_all.py --base_lr 0.05 \
        --batch_size 64 --epochs 100 --weight_decay 5e-4
"""

from __future__ import division
import os

import torch
import torchvision

#import cub200
import pdb
import torchvision.datasets as datasets
import torch.nn.functional as F
from torch.autograd import Variable
from CompactBilinearPooling1 import CompactBilinearPooling
import math

torch.manual_seed(0)
torch.cuda.manual_seed_all(0)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

__all__ = ['BCNN', 'BCNNManager']
__author__ = 'Hao Zhang'
__copyright__ = '2018 LAMDA'
__date__ = '2018-01-09'
__email__ = 'zhangh0214@gmail.com'
__license__ = 'CC BY-SA 3.0'
__status__ = 'Development'
__updated__ = '2018-01-13'
__version__ = '1.2'



input_dim = 512
input_dim1 = 512
input_dim2 = 512
output_dim = 4096

#generate_sketch_matrix = lambda rand_h, rand_s, input_dim, output_dim: torch.sparse.FloatTensor(torch.stack([torch.arange(input_dim, out = torch.LongTensor()), rand_h.long()]), rand_s.float(), [input_dim, output_dim]).to_dense()
#sketch_matrix01 = torch.nn.Parameter(generate_sketch_matrix(torch.randint(output_dim, size = (input_dim1,)), 2 * torch.randint(2, size = (input_dim1,)) - 1, input_dim1, output_dim))
#sketch_matrix02 = torch.nn.Parameter(generate_sketch_matrix(torch.randint(output_dim, size = (input_dim2,)), 2 * torch.randint(2, size = (input_dim2,)) - 1, input_dim2, output_dim))
#sketch_matrix03 = torch.nn.Parameter(generate_sketch_matrix(torch.randint(output_dim, size = (input_dim2,)), 2 * torch.randint(2, size = (input_dim2,)) - 1, input_dim2, output_dim))
#sketch_matrix04 = torch.nn.Parameter(generate_sketch_matrix(torch.randint(output_dim, size = (input_dim2,)), 2 * torch.randint(2, size = (input_dim2,)) - 1, input_dim2, output_dim))
#torch.save(sketch_matrix01,'/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix1_4096.pth')
#torch.save(sketch_matrix02,'/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix2_4096.pth')
#torch.save(sketch_matrix03,'/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix3_4096.pth')
#torch.save(sketch_matrix04,'/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix4_4096.pth')
#pdb.set_trace()

sketch_matrix01 = torch.load('/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix1_4096.pth')
sketch_matrix02 = torch.load('/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix2_4096.pth')
sketch_matrix03 = torch.load('/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix3_4096.pth')
sketch_matrix04 = torch.load('/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/sketch_matrix4_4096.pth')

#a00 = torch.randint(16,28,28,1)s
#gamma = 1e-5
#a0 = math.exp(-2*gamma)
#a1 = a0*(2*gamma)
#a2 = a0*((2*gamma)**2)/2
#a3 = a0*((2*gamma)**3)/3/2
#a4 = a0*((2*gamma)**4)/4/3/2
#pdb.set_trace()

class BCNN(torch.nn.Module):
    """B-CNN for CUB200.

    The B-CNN model is illustrated as follows.
    conv1^2 (64) -> pool1 -> conv2^2 (128) -> pool2 -> conv3^3 (256) -> pool3
    -> conv4^3 (512) -> pool4 -> conv5^3 (512) -> bilinear pooling
    -> sqrt-normalize -> L2-normalize -> fc (200).
    The network accepts a 3*448*448 input, and the pool5 activation has shape
    512*28*28 since we down-sample 5 times.

    Attributes:
        features, torch.nn.Module: Convolution and pooling layers.
        fc, torch.nn.Module: 200.
    """
    def __init__(self):
        """Declare all needed layers."""
        torch.nn.Module.__init__(self)
        # Convolution and pooling layers of VGG-16.
        self.features = torchvision.models.vgg16(pretrained=True).features
        self.features = torch.nn.Sequential(*list(self.features.children())
                                            [:-1])  # Remove pool5.
        # Linear classifier.
        self.fc = torch.nn.Linear(12801, 200)
        for param in self.features.parameters():
            param.requires_grad = False

    def forward(self, X):
        """Forward pass of the network.

        Args:
            X, torch.autograd.Variable of shape N*3*448*448.

        Returns:
            Score, torch.autograd.Variable of shape N*200.
        """
        N = X.size()[0]
#        pdb.set_trace()
        assert X.size() == (N, 3, 448, 448)
        X = self.features(X)
        assert X.size() == (N, 512, 28, 28)
        XV = X.reshape(X.size(0), -1)
        
#        pdb.set_trace()
        sft = 0
        tm = 0
        
        for ii in range(N-1):
            for jj in range(ii+1,N):
                tm = tm+1
                sft = sft + torch.mm(XV[ii,:].view(1,401408),XV[jj,:].view(401408,1))
#        sft = sft.detach()
        if sft == 0:
            gamma = 0
        else:
            gamma = 1/(sft/tm)
#        pdb.set_trace()
        a0 = math.exp(-2*gamma)
        a1 = a0*(2*gamma)
        a2 = a0*((2*gamma)**2)/2
        a3 = a0*((2*gamma)**3)/3/2
        a4 = a0*((2*gamma)**4)/4/3/2       
         
#        pdb.set_trace()        
        
        sketch_matrix1 = sketch_matrix01.cuda()
        sketch_matrix2 = sketch_matrix02.cuda()
        sketch_matrix3 = sketch_matrix03.cuda()
        sketch_matrix4 = sketch_matrix04.cuda()

        fft1 = torch.rfft(X.permute(0, 2, 3, 1).matmul(sketch_matrix1), 1)
        fft2 = torch.rfft(X.permute(0, 2, 3, 1).matmul(sketch_matrix2), 1)
        fft_product1 = torch.stack([fft1[..., 0] * fft2[..., 0] - fft1[..., 1] * fft2[..., 1], fft1[..., 0] * fft2[..., 1] + fft1[..., 1] * fft2[..., 0]], dim = -1)
        cbp2 = torch.irfft(fft_product1, 1, signal_sizes = (output_dim,)) * output_dim
        fft3 = torch.rfft(X.permute(0, 2, 3, 1).matmul(sketch_matrix3), 1)
        fft_product2 = torch.stack([fft_product1[..., 0] * fft3[..., 0] - fft_product1[..., 1] * fft3[..., 1], fft_product1[..., 0] * fft3[..., 1] + fft_product1[..., 1] * fft3[..., 0]], dim = -1)
        cbp3 = torch.irfft(fft_product2, 1, signal_sizes = (output_dim,)) * output_dim
        fft4 = torch.rfft(X.permute(0, 2, 3, 1).matmul(sketch_matrix4), 1)
        fft_product3 = torch.stack([fft_product2[..., 0] * fft4[..., 0] - fft_product2[..., 1] * fft4[..., 1], fft_product2[..., 0] * fft4[..., 1] + fft_product2[..., 1] * fft4[..., 0]], dim = -1)
        cbp4 = torch.irfft(fft_product3, 1, signal_sizes = (output_dim,)) * output_dim
        feat = torch.cat([a0*torch.ones(X.size(0), cbp2.size(1), cbp2.size(2), 1).cuda(), a1*X.permute(0, 2, 3, 1), a2*cbp2, a3*cbp3, a4*cbp4], dim=3)         
#        pdb.set_trace() 
#        XX = X.permute(0, 2, 3, 1).contiguous().view(-1, 512)
        
#        X = torch.matmul(X,X.transpose(1,2))/(28**2)  # Bilinear
#        assert X.size() == (N, 512, 512)
#        X = X.view(N, 512**2)
        feat = feat.sum(dim = 1).sum(dim = 1)
        
#        pdb.set_trace()        
        feat = torch.sqrt(F.relu(feat)) - torch.sqrt(F.relu(-feat))
        feat = torch.nn.functional.normalize(feat)
#        pdb.set_trace()
        feat = self.fc(feat)        
        assert feat.size() == (N, 200)
        return feat


class BCNNManager(object):
    """Manager class to train bilinear CNN.

    Attributes:
        _options: Hyperparameters.
        _path: Useful paths.
        _net: Bilinear CNN.
        _criterion: Cross-entropy loss.
        _solver: SGD with momentum.
        _scheduler: Reduce learning rate by a fator of 0.1 when plateau.
        _train_loader: Training data.
        _test_loader: Testing data.
    """
    def __init__(self, options, path):
        """Prepare the network, criterion, solver, and data.

        Args:
            options, dict: Hyperparameters.
        """
        print('Prepare the network and data.')
        self._options = options
        self._path = path
#        pdb.set_trace()
        # Network.
        self._net = torch.nn.DataParallel(BCNN()).cuda()
        # Load the model from disk.
#        self._net.load_state_dict(self.load_my_state_dict(torch.load(self._path['model'])))
#        self._net.load_state_dict(torch.load(self._path['model']))
        print(self._net)
        # Criterion.
        self._criterion = torch.nn.CrossEntropyLoss().cuda()
        # Solver.
#        self._solver = torch.optim.SGD(
#            self._net.module.fc.parameters(), lr=self._options['base_lr'],
#            momentum=0.9, weight_decay=self._options['weight_decay'])
        self._solver = torch.optim.Adam(
            self._net.module.fc.parameters(), lr=self._options['base_lr'],
            weight_decay=self._options['weight_decay'])
        self._scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self._solver, mode='max', factor=0.65, patience=5, verbose=True,
            threshold=1e-4)

        train_transforms = torchvision.transforms.Compose([
            torchvision.transforms.Resize(size=448),  # Let smaller edge match
            torchvision.transforms.RandomHorizontalFlip(),
            torchvision.transforms.RandomCrop(size=448),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(mean=(0.485, 0.456, 0.406),
                                             std=(0.229, 0.224, 0.225))
        ])
        test_transforms = torchvision.transforms.Compose([
            torchvision.transforms.Resize(size=448),
            torchvision.transforms.CenterCrop(size=448),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(mean=(0.485, 0.456, 0.406),
                                             std=(0.229, 0.224, 0.225))
        ])
        data_dir1 = '/media/tiantong/Drive/Xuelu/CUB_200_2011/train'
        train_data = datasets.ImageFolder(root=data_dir1,transform=train_transforms)
        data_dir2 = '/media/tiantong/Drive/Xuelu/CUB_200_2011/test'
        test_data = datasets.ImageFolder(root=data_dir2,transform=test_transforms)
        self._train_loader = torch.utils.data.DataLoader(
            train_data, batch_size=self._options['batch_size'],
            shuffle=True, num_workers=4, pin_memory=True)
        self._test_loader = torch.utils.data.DataLoader(
            test_data, batch_size=8,
            shuffle=False, num_workers=4, pin_memory=True)

    def train(self):
        """Train the network."""
        print('Training.')
        best_acc = 0.0
        best_epoch = None
        print('Epoch\tTrain loss\tTrain acc\tTest acc')
        for t in range(self._options['epochs']):
            epoch_loss = []
            num_correct = 0
            num_total = 0
            u = 0
            for X, y in self._train_loader:
                u = u+1
#                if u == 375:
#                pdb.set_trace()
                # Data.
                X = torch.autograd.Variable(X.cuda())
                y = torch.autograd.Variable(y.cuda(async=True))

                # Clear the existing gradients.
                self._solver.zero_grad()
                # Forward pass.
                score = self._net(X)
#                pdb.set_trace()
                loss = self._criterion(score, y)
#                print('| Epoch %2d Iter %3d\tBatch loss %.4f\t' % (t+1,u,loss))
                epoch_loss.append(loss.item())
                # Prediction.
                _, prediction = torch.max(score.data, 1)
                num_total += y.size(0)
                num_correct += torch.sum(prediction == y.data).item()
                # Backward pass.
                loss.backward()
                self._solver.step()

            train_acc = 100 * num_correct / num_total
            test_acc = self._accuracy(self._test_loader)
            self._scheduler.step(test_acc)
            if test_acc > best_acc:
                best_acc = test_acc
                best_epoch = t + 1
#                print('*', end='')
# Save model onto disk.
                torch.save(self._net.state_dict(),
                           os.path.join('/media/tiantong/Drive/Xuelu/CUB_200_2011/bilinear-cnn1/model',
                                        'kernel_vgg_16_epoch_%d.pth' % (t + 1)))
            print('%d\t%4.3f\t\t%4.2f%%\t\t%4.2f%%' %
                  (t+1, sum(epoch_loss) / len(epoch_loss), train_acc, test_acc))
        print('Best at epoch %d, test accuaray %f' % (best_epoch, best_acc))

    def _accuracy(self, data_loader):
        
        """Compute the train/test accuracy.

        Args:
            data_loader: Train/Test DataLoader.

        Returns:
            Train/Test accuracy in percentage.
        """
        self._net.train(False)
        torch.no_grad()
        num_correct = 0
        num_total = 0
        for X, y in data_loader:
            # Data.

            X = torch.autograd.Variable(X.cuda())
            y = torch.autograd.Variable(y.cuda(async=True))
#            X = X.to(device)
#            y = y.to(device)

            # Prediction.
#            pdb.set_trace()
            score = self._net(X)
            _, prediction = torch.max(score.data, 1)
            num_total += y.size(0)
            num_correct += torch.sum(prediction == y.data).item()
#            del X, y
        self._net.train(True)  # Set the model to training phase
        return 100 * num_correct / num_total

def main():
    """The main function."""

    options = {
        'base_lr': 0.01,
        'batch_size': 66,
        'epochs': 150,
        'weight_decay': 1e-5,
    }

    project_root = os.popen('pwd').read().strip()
    path = {
#        'cub200': os.path.join(project_root, 'data/cub200'),
        'model': os.path.join(project_root, 'model'),
    }
    for d in path:
        assert os.path.isdir(path[d])
   
#    pdb.set_trace()
#        else:
#            assert os.path.isdir(path[d])

    manager = BCNNManager(options, path)
    # manager.getStat()
    manager.train()


if __name__ == '__main__':
    main()
