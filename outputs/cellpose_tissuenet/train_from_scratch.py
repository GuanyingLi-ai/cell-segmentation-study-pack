#!/usr/bin/env python3
from pathlib import Path
import json, platform, time
import numpy as np, torch
from cellpose import io, models, train

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/human_in_the_loop'
OUT=ROOT/'outputs/scratch_legacy_architecture'

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 images,labels,names,test_images,test_labels,test_names=io.load_train_test_data(
  str(DATA/'train'),str(DATA/'test'),mask_filter='_seg.npy')
 np.random.seed(0);torch.manual_seed(0)
 # Same two-channel Cellpose architecture, but no pretrained checkpoint.
 model=models.CellposeModel(gpu=False,pretrained_model=False,model_type=None,nchan=2,diam_mean=30.0)
 start=time.perf_counter()
 path,train_losses,test_losses=train.train_seg(
  model.net,train_data=images,train_labels=labels,test_data=test_images,test_labels=test_labels,
  channels=[2,1],batch_size=5,learning_rate=0.005,n_epochs=100,weight_decay=1e-5,
  SGD=False,rescale=True,bsize=224,min_train_masks=5,save_path=OUT,save_every=25,
  model_name='tissuenet_hil_scratch_seed0')
 report={'status':'success','scope':'Cellpose architecture trained from random initialization on 5 labelled TissueNet HIL images',
  'initialization':'random','checkpoint':str(path),'n_train_images':len(images),'n_test_images':len(test_images),
  'parameters':{'channels':[2,1],'batch_size':5,'learning_rate':0.005,'n_epochs':100,'weight_decay':1e-5,'SGD':False,'rescale':True,'bsize':224,'seed':0,'nchan':2,'diam_mean':30.0},
  'environment':{'python':platform.python_version(),'torch':torch.__version__,'device':'cpu'},
  'runtime_seconds':time.perf_counter()-start,'train_losses':[float(x) for x in train_losses],
  'test_losses':[float(x) for x in test_losses]}
 (OUT/'training_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['checkpoint','runtime_seconds']},indent=2))
if __name__=='__main__':main()
