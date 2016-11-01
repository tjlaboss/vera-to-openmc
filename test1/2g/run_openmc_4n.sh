#! /bin/bash
#
# partition (queue) 
#SBATCH -p fast
#
# number of nodes 
#SBATCH -N 1 
#
# number of cores 
#SBATCH -n 4 
#
# memory pool for all cores 
#  comment SBATCH --mem 100 
#
# time (D-HH:MM) 
#  comment SBATCH -t 0-8:00 
#
# STDOUT 
#SBATCH -o Results.%N.%j.out 
# STDERR 
#SBATCH -e slurm.%N.%j.err 
# notifications for job done & fail 
#SBATCH --mail-type=END,FAIL 
# send-to address
#SBATCH --mail-user=travis.labossiere@gmail.com


export OPENMC_CROSS_SECTIONS=$MCNPXS
openmc
