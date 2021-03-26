import tensorflow as tf
import numpy as np
from numpy.random import random
import torch
from .base_wrapper import concat_, unconcat_, BaseWrapper
from torch.autograd.functional import hvp, vhp, hessian


class TorchWrapper(BaseWrapper):
    def __init__(self, func, precision='float32', hvp_type='hvp'):
        self.func = func

        if precision == 'float32':
            self.precision = torch.float32
        elif precision == 'float64':
            self.precision = torch.float64
        else:
            raise ValueError
        
        self.hvp_func = hvp if hvp_type=='hvp' else vhp

    def get_input(self, input_var):
        input_, self.shapes = concat_(input_var)
        return input_

    def get_output(self, output_var):
        assert 'shapes' in dir(self), 'You must first call get input to define the tensors shapes.'
        output_var_ = unconcat_(output_var, self.shapes)
        return output_var_

    def get_bounds(self, bounds):
        return bounds

    def get_constraints(self, constraints):
        return constraints

    def get_value_and_grad(self, input_var):
        assert 'shapes' in dir(self), 'You must first call get input to define the tensors shapes.'

        input_var_ = unconcat_(torch.tensor(
            input_var, dtype=self.precision, requires_grad=True), self.shapes)
        
        loss = self._eval_func(input_var_)
        input_var_grad = input_var_.values() if isinstance(input_var_, dict) else input_var_
        grads = torch.autograd.grad(loss, input_var_grad)

        if isinstance(input_var_, dict):
            grads = {k:v for k, v in zip(input_var_.keys(), grads)}

        return [loss.cpu().detach().numpy().astype(np.float64), 
            concat_(grads)[0].cpu().detach().numpy().astype(np.float64)]

    def get_hvp(self, input_var, vector):
        assert 'shapes' in dir(self), 'You must first call get input to define the tensors shapes.'
        input_var_ = unconcat_(torch.tensor(
            input_var, dtype=self.precision, requires_grad=True), self.shapes)
        vector_ = unconcat_(torch.tensor(
            vector, dtype=self.precision), self.shapes)

        loss, vhp_res = self.hvp_func(self._eval_func, input_var_, v=vector_)

        return concat_(vhp_res)[0].cpu().detach().numpy().astype(np.float64)

    def get_hess(self, input_var):
        assert 'shapes' in dir(self), 'You must first call get input to define the tensors shapes.'
        input_var_ = torch.tensor(input_var, dtype=self.precision)

        hess = torch.autograd.functional.hessian(self._eval_func, 
            unconcat_(input_var_, self.shapes),
            vectorize=False).cpu().detach().numpy().astype(np.float64)

        return hess