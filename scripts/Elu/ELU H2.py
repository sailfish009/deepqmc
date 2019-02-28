import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import time
import torch
import torch.nn as nn
from torch.autograd import Variable,grad
import torch.nn.functional as F
from torch.nn.utils import clip_grad_norm_
import copy
import datetime

cmap=plt.get_cmap("plasma")


def metropolis(distribution,startpoint,maxstepsize,steps,presteps=0,interval=None):
	#initialise list to store walker positions
	samples = torch.zeros(steps,len(startpoint))
	#initialise the walker at the startposition
	walker = torch.tensor([startpoint]).type(torch.FloatTensor)
	distwalker = distribution(walker)
	#loop over proposal steps
	for i in range(presteps+steps):
		#append position of walker to the sample list in case presteps exceeded
		if i > (presteps-1):
			samples[i-presteps]=(walker)
		#propose new trial position
		trial = walker + (torch.rand(6)-0.5)*maxstepsize
		#calculate acceptance propability
		disttrial = distribution(trial)
		#check if in interval
		if not interval is None:
			inint = torch.tensor(all(torch.tensor(interval[0]).type(torch.FloatTensor)<trial[0]) \
			and all(torch.tensor(interval[1]).type(torch.FloatTensor)>trial[0])).type(torch.FloatTensor)
			disttrial = disttrial*inint

		ratio = disttrial/distwalker
		#accept trial position with respective propability
		if ratio > np.random.uniform(0,1):
			walker = trial
			distwalker = disttrial
	#return list of samples
	return samples

def fit(batch_size=2056,steps=15,epochs=4,R1=1.5,R2=-1.5,losses=["variance","energy","symmetry"]):
	class Net(nn.Module):
		def __init__(self):
			super(Net, self).__init__()
			self.NN=nn.Sequential(
					torch.nn.Linear(5, 64),
					torch.nn.ELU(),
					torch.nn.Linear(64, 64),
					torch.nn.ELU(),
					#torch.nn.Linear(64, 64),
					#torch.nn.ELU(),
					torch.nn.Linear(64, 64),
					torch.nn.ELU(),
					torch.nn.Linear(64, 1)
					)
			#self.Lambda=nn.Parameter(torch.Tensor([-1]))	#eigenvalue

		def forward(self,x):
			d = torch.zeros(len(x),5)
			d[:,0] = torch.norm(x[:,:3]-R1,dim=1)
			d[:,1] = torch.norm(x[:,:3]-R2,dim=1)
			d[:,2] = torch.norm(x[:,3:]-R1,dim=1)
			d[:,3] = torch.norm(x[:,3:]-R2,dim=1)
			d[:,4] = torch.norm(x[:,:3]-x[:,3:],dim=1)
			d2     = torch.zeros(len(x),5)
			d2[:,2] = d[:,0]
			d2[:,3] = d[:,1]
			d2[:,0] = d[:,2]
			d2[:,1] = d[:,3]
			d2[:,4] = d[:,4]
			r = torch.erf(d/0.5)/d
			r2 = torch.erf(d2/0.05)/d2
			return (self.NN(r)[:,0]+self.NN(r2)[:,0])

	LR=2e-3

	R1    = torch.tensor([R1,0,0]).type(torch.FloatTensor)
	R2    = torch.tensor([R2,0,0]).type(torch.FloatTensor)
	R     = torch.norm(R1-R2)

	X_plot = torch.from_numpy(np.swapaxes(np.array([np.linspace(-6,6,100),np.zeros(100),np.zeros(100),3*np.ones(100),np.zeros(100),np.zeros(100)]).reshape(6,100),0,1)).type(torch.FloatTensor)

	net = Net()
	params = [p for p in net.parameters()]
	#del params[0]
	#del params[1]
	#del params[1]
	opt = torch.optim.Adam(params, lr=LR)
	scheduler = torch.optim.lr_scheduler.StepLR(opt, step_size=1, gamma=0.5)

	E = 100
	E_min = 100


	plt.figure(figsize=(12,9))
	plt.subplots_adjust(bottom=0.3)
	for epoch in range(epochs):
		scheduler.step()

		savenet = (copy.deepcopy(net),E)


		print("epoch " +str(1+epoch)+" of "+str(epochs)+":")

		if losses[epoch%len(losses)] == "energy":
			print("minimize energy")
		elif losses[epoch%len(losses)] == "variance":
			print("minimize variance of energy")
		else:
			print("loss error, check losses:"+str(losses[epoch%len(losses)] ))

		print("current LR = " + str(opt.state_dict()["param_groups"][0]["lr"]))

		start = time.time()


		X_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,6))*3*R.numpy()).type(torch.FloatTensor)
		#X1_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,1))*3/2*R.numpy()).type(torch.FloatTensor)
		#X2_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,1))*3/2*R.numpy()).type(torch.FloatTensor)
		#X3_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,1))*3/2*R.numpy()).type(torch.FloatTensor)
		#X4_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,1))*3/2*R.numpy()).type(torch.FloatTensor)
		#X5_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,1))*3/2*R.numpy()).type(torch.FloatTensor)
		#X6_all = torch.from_numpy(np.random.normal(0,1,(batch_size*steps,1))*3/2*R.numpy()).type(torch.FloatTensor)
		#XS_all  = torch.cat([X1_all,X2_all,X3_all], dim=0).reshape(3,batch_size*steps).transpose(0,1)

		index = torch.randperm(steps*batch_size)
		X_all.requires_grad = True
		#X1_all.requires_grad = True
		#X2_all.requires_grad = True
		#X3_all.requires_grad = True
		#X4_all.requires_grad = True
		#X5_all.requires_grad = True
		#X6_all.requires_grad = True

		for step in range(steps):

			if losses[epoch%len(losses)] == "energy":

				X = X_all[index[step*batch_size:(step+1)*batch_size]]


				r1    = torch.norm(X[:,:3]-R1,dim=1)
				r2    = torch.norm(X[:,:3]-R2,dim=1)
				r3    = torch.norm(X[:,3:]-R1,dim=1)
				r4    = torch.norm(X[:,3:]-R2,dim=1)
				r5    = torch.norm(X[:,:3]-X[:,3:],dim=1)
				V     = -1/r1 - 1/r2 - 1/r3 - 1/r4 + 1/r5
				Psi=net(X).flatten()

				g = torch.autograd.grad(Psi,X,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
				gradloss  = torch.sum(0.5*(torch.sum(g**2,dim=1)) + Psi**2*V)/torch.sum(Psi**2)
				J = gradloss #+ (torch.sum(Psi**2)-1)**2

			# elif losses[epoch%len(losses)] == "variance":
			#
			# 	X1 = X1_all[index[step*batch_size:(step+1)*batch_size]]
			# 	X2 = X2_all[index[step*batch_size:(step+1)*batch_size]]
			# 	X3 = X3_all[index[step*batch_size:(step+1)*batch_size]]
			# 	X4 = X4_all[index[step*batch_size:(step+1)*batch_size]]
			# 	X5 = X5_all[index[step*batch_size:(step+1)*batch_size]]
			# 	X6 = X6_all[index[step*batch_size:(step+1)*batch_size]]
			# 	X=torch.cat([X1,X2,X3,X4,X5,X6], dim=0).reshape(6,batch_size).transpose(0,1)
			#
			# 	Psi=net(X).flatten()
			# 	dx1 =torch.autograd.grad(Psi,X1,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))
			# 	ddx1=torch.autograd.grad(dx1[0].flatten(),X1,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
			# 	dy1 =torch.autograd.grad(Psi,X2,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))
			# 	ddy1=torch.autograd.grad(dy1[0].flatten(),X2,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
			# 	dz1 =torch.autograd.grad(Psi,X3,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))
			# 	ddz1=torch.autograd.grad(dz1[0].flatten(),X3,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
			# 	dx2 =torch.autograd.grad(Psi,X4,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))
			# 	ddx2=torch.autograd.grad(dx2[0].flatten(),X4,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
			# 	dy2 =torch.autograd.grad(Psi,X5,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))
			# 	ddy2=torch.autograd.grad(dy2[0].flatten(),X5,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
			# 	dz2 =torch.autograd.grad(Psi,X6,create_graph=True,retain_graph=True,grad_outputs=torch.ones(batch_size))
			# 	ddz2=torch.autograd.grad(dz2[0].flatten(),X6,retain_graph=True,grad_outputs=torch.ones(batch_size))[0]
			# 	lap_X = (ddx1+ddy1+ddz1+ddx2+ddy2+ddz2).flatten()
			#
			#
			# 	r1    = torch.norm(X[:,:3]-R1,dim=1)
			# 	r2    = torch.norm(X[:,:3]-R2,dim=1)
			# 	r3    = torch.norm(X[:,3:]-R1,dim=1)
			# 	r4    = torch.norm(X[:,3:]-R2,dim=1)
			# 	r5    = torch.norm(X[:,:3]-X[:,3:],dim=1)
			# 	V     = -1/r1 - 1/r2 - 1/r3 - 1/r4 + 1/r5
			#
			#
			#
			# 	#laploss  = torch.sqrt(torch.sum((-0.5*lap_X*Psi + (V-net.Lambda)*Psi**2)**2))*1e1
			#
			#
			# 	#gradloss  = torch.sum(0.5*(dx[0]**2+dy[0]**2+dz[0]**2) + Psi**2*(V))
			# 	laploss  = torch.sum(Psi*(-0.5*lap_X + Psi*V)) * 11000
			# 	#print(gradloss/laploss)
			#
			#
			#
			# 	#laploss  = torch.sum((-0.5*lap_X + (V-net.Lambda)*Psi)**2/(Psi**2))#/torch.sum(Psi**2)
			#
			# 	J = laploss + (torch.sum(Psi**2)-1)**2

			opt.zero_grad()
			J.backward()
			for p in net.parameters():
				print(p)
				p.grad = p.grad*(p.grad==0).type(torch.FloatTensor)
			grads=(np.array([p for p in net.parameters()][0].grad))
			print(np.max(grads),np.min(grads),np.mean(grads))
			opt.step()


			print("Progress {:2.0%}".format(step /steps), end="\r")


		for m in [30000,30000,30000]:#,25000,50000]:
			t = time.time()

			samples=metropolis(lambda x :net(x)**2,np.array([1,0,0,-1,0,0]),2,m,presteps=500)
			X1 = samples[:,0]
			X2 = samples[:,1]
			X3 = samples[:,2]
			X4 = samples[:,3]
			X5 = samples[:,4]
			X6 = samples[:,5]
			X1.requires_grad=True
			X2.requires_grad=True
			X3.requires_grad=True
			X4.requires_grad=True
			X5.requires_grad=True
			X6.requires_grad=True
			X=torch.cat([X1,X2,X3,X4,X5,X6], dim=0).reshape(6,m).transpose(0,1)
			Psi=net(X).flatten()
			dx1 =torch.autograd.grad(Psi,X1,create_graph=True,retain_graph=True,grad_outputs=torch.ones(m))
			ddx1=torch.autograd.grad(dx1[0].flatten(),X1,retain_graph=True,grad_outputs=torch.ones(m))[0]
			dy1 =torch.autograd.grad(Psi,X2,create_graph=True,retain_graph=True,grad_outputs=torch.ones(m))
			ddy1=torch.autograd.grad(dy1[0].flatten(),X2,retain_graph=True,grad_outputs=torch.ones(m))[0]
			dz1 =torch.autograd.grad(Psi,X3,create_graph=True,retain_graph=True,grad_outputs=torch.ones(m))
			ddz1=torch.autograd.grad(dz1[0].flatten(),X3,retain_graph=True,grad_outputs=torch.ones(m))[0]
			dx2 =torch.autograd.grad(Psi,X4,create_graph=True,retain_graph=True,grad_outputs=torch.ones(m))
			ddx2=torch.autograd.grad(dx2[0].flatten(),X4,retain_graph=True,grad_outputs=torch.ones(m))[0]
			dy2 =torch.autograd.grad(Psi,X5,create_graph=True,retain_graph=True,grad_outputs=torch.ones(m))
			ddy2=torch.autograd.grad(dy2[0].flatten(),X5,retain_graph=True,grad_outputs=torch.ones(m))[0]
			dz2 =torch.autograd.grad(Psi,X6,create_graph=True,retain_graph=True,grad_outputs=torch.ones(m))
			ddz2=torch.autograd.grad(dz2[0].flatten(),X6,retain_graph=True,grad_outputs=torch.ones(m))[0]
			lap_X = (ddx1+ddy1+ddz1+ddx2+ddy2+ddz2).flatten()

			r1    = torch.norm(X[:,:3]-R1,dim=1)
			r2    = torch.norm(X[:,:3]-R2,dim=1)
			r3    = torch.norm(X[:,3:]-R1,dim=1)
			r4    = torch.norm(X[:,3:]-R2,dim=1)
			r5    = torch.norm(X[:,:3]-X[:,3:],dim=1)
			V     = -1/r1 - 1/r2 - 1/r3 - 1/r4 + 1/r5 + 1/R
			E_loc_lap = -0.5*lap_X/Psi
			# plt.figure()
			# plt.plot(X1.detach().numpy(),(V).detach().numpy(),ls='',marker='.',label='Potential',color='y',ms=1)
			# plt.plot(X1.detach().numpy(),(E_loc_lap).detach().numpy(),ls='',marker='.',label='Laplacian/Psi',color='r',ms=1)
			# plt.plot(X1.detach().numpy(),(E_loc_lap + V).detach().numpy(),ls='',marker='.',label='Local energy (sum)',color='g',ms=1)
			# plt.show()
			E = (torch.mean(E_loc_lap + V).item()*27.211386)
			print(E,time.time()-t)

		print('___________________________________________')
		print('It took', time.time()-start, 'seconds.')
		print('Lambda = '+str(net.Lambda[0].item()*27.2))
		print('Energy = '+str(E))
		print('\n')


		# if E < E_min:
		# 	E_min = E
		# 	Psi_min = copy.deepcopy(net)
		#
		# if False:#epoch > 1 and E > (savenet[1]+10*(1-epoch/epochs)**2):
		# 	print("undo step as E_new = "+str(E)+" E_old = "+str(savenet[1]))
		#
		# 	Psi_plot = net(X_plot).detach().numpy()
		# 	if Psi_plot[np.argmax(np.abs(Psi_plot))] < 0:
		# 		print("negative Psi")
		# 	#	Psi_plot *= -1
		# 	plt.plot(X_plot[:,0].numpy(),(Psi_plot/max(np.abs(Psi_plot)))**2,label=str(np.round(E,2)),ls=':',color='grey',linewidth =1)
		#
		# 	net = savenet[0]
		# 	E   = savenet[1]
		#
		# 	params = [p for p in net.parameters()]
		# 	del params[0]
		# 	opt = torch.optim.Adam(params, lr=LR)
		#
		if True:#else:

			Psi_plot = net(X_plot).detach().numpy()
			if Psi_plot[np.argmax(np.abs(Psi_plot))] < 0:
				print("negative Psi")
				#Psi_plot *= -1

			if epoch<(epochs-1) :
				plt.plot(X_plot[:,0].numpy(),(Psi_plot/max(np.abs(Psi_plot)))**2,label=str(np.round(E,2)),ls=':',color=cmap(epoch/epochs),linewidth =2)

			else:
				plt.plot(X_plot[:,0].numpy(),(Psi_plot/max(np.abs(Psi_plot)))**2,label=str(np.round(E,2)),color='k',linewidth =3)
				#plt.plot(X_plot[:,0].numpy(),Decay/max(Decay))
				#plt.plot(X_plot[:,0].numpy(),(Psi_plot2/max(np.abs(Psi_plot2)))**2,label=str(np.round(E,2)),color='k',linewidth =2)
			#plt.hist(X_all.detach().numpy()[:,0],density=True)
			#plt.show()

	plt.axvline(R1.numpy()[0],ls=':',color='k')
	plt.axvline(R2.numpy()[0],ls=':',color='k')

	plt.title("batch_size = "+str(batch_size)+", steps = "+str(steps)+", epochs = "+str(epochs)+", R = "+str(R.item())+", losses = "+str(losses))
	plt.legend(loc="lower center",bbox_to_anchor=[0.5, - 0.4], ncol=8)
	#plt.savefig(datetime.datetime.now().strftime("%B%d%Y%I%M%p")+".png")
	plt.show()
	#return (Psi_min,E_min)
#	fig = plt.figure()
#	ax = fig.add_subplot(1, 1, 1, projection='3d')
#	ax.scatter(X1.detach().numpy(), X2.detach().numpy(), X3.detach().numpy(), c=np.abs(Psi.detach().numpy()), cmap=plt.hot())
#	plt.show()
fit(batch_size=1000,steps=1000,epochs=5,losses=["energy"],R1=0.9,R2=-0.9)