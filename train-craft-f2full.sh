#!/usr/bin/env bash
torchrun --nproc_per_node 2 train.py --name craft-chairs --stage chairs --validation chairs --output results/chairs/craft-f2full --num_steps 120000 --lr 0.00025 --image_size 368 496 --wdecay 0.0001 --gpus 0 1 --batch_size 4 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
torchrun --nproc_per_node 2 train.py --name craft-things --stage things --validation sintel --output results/things/craft-f2full --restore_ckpt results/chairs/craft-f2full/craft-chairs.pth --num_steps 120000 --lr 0.000125 --image_size 400 720 --wdecay 0.0001 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
torchrun --nproc_per_node 2 train.py --name craft-sintel --stage sintel --validation sintel --output results/sintel/craft-f2full --restore_ckpt results/things/craft-f2full/craft-things.pth --num_steps 120000 --lr 0.000125 --image_size 368 768 --wdecay 0.00001 --gamma 0.85 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
torchrun --nproc_per_node 2 train.py --name craft-kitti --stage kitti --validation kitti --output results/kitti/craft-f2full --restore_ckpt results/sintel/craft-f2full/craft-sintel.pth --num_steps 50000 --lr 0.000125 --image_size 288 960 --wdecay 0.00001 --gamma 0.85 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
torchrun --nproc_per_node 2 train.py --name craft-viper --stage viper --validation viper --output results/viper/craft-f2full --restore_ckpt results/sintel/craft-f2full/craft-sintel.pth --num_steps 50000 --lr 0.000125 --image_size 288 960 --wdecay 0.00001 --gamma 0.85 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
# Autoflow training
torchrun --nproc_per_node 2 train.py --name craft-autoflow --stage autoflow --validation sintel --output results/autoflow/craft-f2full --num_steps 200000 --lr 0.000125 --image_size 488 576 --wdecay 0.0001 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
torchrun --nproc_per_node 2 train.py --name craft-sintel --stage sintel --validation sintel --output results/sintel/craft-f2full-autoflow --restore_ckpt results/autoflow/craft-f2full/craft-autoflow.pth --num_steps 120000 --lr 0.000125 --image_size 368 768 --wdecay 0.00001 --gamma 0.85 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
torchrun --nproc_per_node 2 train.py --name craft-kitti --stage kitti --validation kitti --output results/kitti/craft-f2full-autoflow --restore_ckpt results/sintel/craft-f2full-autoflow/craft-sintel.pth --num_steps 50000 --lr 0.000125 --image_size 288 960 --wdecay 0.00001 --gamma 0.85 --gpus 0 1 --batch_size 3 --val_freq 10000 --print_freq 100 --mixed_precision --craft --f2 full --setrans
