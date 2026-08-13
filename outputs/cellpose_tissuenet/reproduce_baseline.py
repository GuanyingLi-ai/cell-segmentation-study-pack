#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, platform, time
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, tifffile, torch
from cellpose import models, plot
from scipy.optimize import linear_sum_assignment

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/human_in_the_loop/test'
DEFAULT_MODEL=Path('/Users/liguanying/Desktop/cell-segmentation-study-pack/cache/cellpose-models/cytotorch_0')

def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def stats(gt,pred,thr):
 ng,npr=int(gt.max()),int(pred.max()); ov=np.zeros((ng+1,npr+1),np.int64)
 np.add.at(ov,(gt.ravel(),pred.ravel()),1); inter=ov[1:,1:]
 ga=np.bincount(gt.ravel(),minlength=ng+1)[1:,None];pa=np.bincount(pred.ravel(),minlength=npr+1)[1:][None,:]
 iou=np.divide(inter,ga+pa-inter,out=np.zeros_like(inter,float),where=(ga+pa-inter)>0)
 if ng and npr:
  r,c=linear_sum_assignment(-iou); scores=iou[r,c]; ok=scores>=thr; tp=int(ok.sum()); ss=scores[ok]
 else:tp=0;ss=np.array([])
 fp=npr-tp;fn=ng-tp;p=tp/(tp+fp) if tp+fp else 0;rcl=tp/(tp+fn) if tp+fn else 0;f=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0;m=float(ss.mean()) if tp else 0
 return dict(tp=tp,fp=fp,fn=fn,precision=p,recall=rcl,f1=f,mean_matched_iou=m,pq=f*m,n_true=ng,n_pred=npr)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',type=Path,default=DEFAULT_MODEL);ap.add_argument('--name',default='baseline_legacy_cyto');args=ap.parse_args()
 OUT=ROOT/'outputs'/args.name;MODEL=args.model
 for d in [OUT,OUT/'masks',OUT/'figures']:d.mkdir(parents=True,exist_ok=True)
 model=models.CellposeModel(gpu=False,pretrained_model=str(MODEL))
 rows=[]; thrs=[.5,.75,.9]; totals={str(t):dict(tp=0,fp=0,fn=0,iou_sum=0.) for t in thrs}; start=time.perf_counter()
 for p in sorted(DATA.glob('*.tif')):
  im=tifffile.imread(p); seg=np.load(p.with_name(p.stem+'_seg.npy'),allow_pickle=True).item();gt=np.asarray(seg['masks']);channels=[int(x) for x in seg.get('chan_choose',[2,1])]
  t=time.perf_counter(); pred,flows,_=model.eval(im,channels=channels,diameter=30.,flow_threshold=.4,cellprob_threshold=0.,min_size=15);run=time.perf_counter()-t;pred=np.asarray(pred,np.uint16)
  tifffile.imwrite(OUT/'masks'/f'{p.stem}_masks.tif',pred)
  row=dict(image=p.name,input_sha256=sha(p),channels=channels,ground_truth_instances=int(gt.max()),predicted_instances=int(pred.max()),runtime_seconds=run)
  for thr in thrs:
   s=stats(gt,pred,thr);row[str(thr)]=s;a=totals[str(thr)];a['tp']+=s['tp'];a['fp']+=s['fp'];a['fn']+=s['fn'];a['iou_sum']+=s['mean_matched_iou']*s['tp']
  rows.append(row)
  fig,ax=plt.subplots(1,4,figsize=(14,4),constrained_layout=True);ax[0].imshow(im[0],cmap='gray');ax[0].set_title('channel 1');ax[1].imshow(im[1],cmap='gray');ax[1].set_title('channel 2');ax[2].imshow(gt,cmap='nipy_spectral');ax[2].set_title(f'GT n={gt.max()}');ax[3].imshow(plot.mask_overlay(np.moveaxis(im,0,-1),pred));ax[3].set_title(f'cyto n={pred.max()}')
  for x in ax:x.axis('off')
  fig.savefig(OUT/'figures'/f'{p.stem}_qc.png',dpi=160);plt.close(fig)
 agg={}
 for thr in thrs:
  a=totals[str(thr)];tp,fp,fn=a['tp'],a['fp'],a['fn'];pr=tp/(tp+fp);rc=tp/(tp+fn);f=2*tp/(2*tp+fp+fn);mi=a['iou_sum']/tp if tp else 0;agg[str(thr)]=dict(tp=tp,fp=fp,fn=fn,precision=pr,recall=rc,f1=f,mean_matched_iou=mi,pq=f*mi,n_true=sum(r['ground_truth_instances'] for r in rows),n_pred=sum(r['predicted_instances'] for r in rows))
 report=dict(status='success',scope='legacy cyto pretrained quantitative baseline; no training',dataset='Cellpose 2.0 human-in-the-loop TissueNet test',dataset_archive_sha256='f94ea40a7f54fbb1af2e1ffcbed87cd4be7db53db1d3b7d79f4ec6eeef5696ee',model=str(MODEL),model_sha256=sha(MODEL),parameters=dict(diameter=30.,flow_threshold=.4,cellprob_threshold=0.,min_size=15),environment=dict(python=platform.python_version(),torch=torch.__version__,device='cpu'),runtime_seconds=time.perf_counter()-start,aggregate=agg,per_image=rows)
 (OUT/'metrics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(agg,indent=2))
if __name__=='__main__':main()
