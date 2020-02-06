import tensorflow as tf
import qriemannopt.manifold as m

class SGD(tf.optimizers.Optimizer):

    def __init__(self,
                 manifold,
                 learning_rate=0.01,
                 momentum=0.0,
                 name="SGD"):
        """Constructs a new Stochastic Gradient Descent optimizer on Stiefel
        manifold.
        Comment:
            The StiefelSGD works only with real valued tf.Variable of shape
            (..., q, p, 2), where ... -- enumerates manifolds 
            (can be either empty or any shaped),
            q and p size of an isometric matrix, the last index marks
            real and imag parts of an isometric matrix
            (0 -- real part, 1 -- imag part)
        Args:
            learning_rate: floating point number. The learning rate.
            Defaults to 0.01.
            name: Optional name prefix for the operations created when applying
            gradients.  Defaults to 'StiefelSGD'."""
        
        super(SGD, self).__init__(name)
        self.manifold = manifold
        self._lr = learning_rate
        self._lr_t = self._lr_t = tf.convert_to_tensor(self._lr, name="learning_rate")
        self._momentum = False
        if isinstance(momentum, tf.Tensor) or callable(momentum) or momentum > 0:
            self._momentum = True
        if isinstance(momentum, (int, float)) and (momentum < 0 or momentum > 1):
            raise ValueError("`momentum` must be between [0, 1].")
        self.momentum = momentum


    def _create_slots(self, var_list):
        # create momentum slot if necessary
        if self._momentum:
            for var in var_list:
                self.add_slot(var, "momentum")


    def _resource_apply_dense(self, grad, var):

        #Complex version of grad and var
        complex_var = m.real_to_complex(var)
        complex_grad = m.real_to_complex(grad)

        #tf version of learning rate
        lr_t = tf.cast(self._lr_t, complex_var.dtype)

        #Riemannian gradient
        grad_proj = self.manifold.egrad_to_rgrad(complex_var, complex_grad)

        #Upadte of vars (step and retruction)
        if self._momentum:
            #Update momentum
            momentum_var = self.get_slot(var, "momentum")
            momentum_complex = m.real_to_complex(momentum_var)
            momentum_complex = self.momentum * momentum_complex +\
            (1 - self.momentum) * grad_proj

            #Transport and retruction
            new_var, momentum_complex =\
            self.manifold.retraction_transport(complex_var,
                                               momentum_complex,
                                               -lr_t * momentum_complex)
            
            momentum_var.assign(m.complex_to_real(momentum_complex))
        else:
            #New value of var
            new_var = self.manifold.retraction(complex_var, -lr_t * grad_proj)

        #Update of var
        var.assign(m.complex_to_real(new_var))

    def _resource_apply_sparse(self, grad, var):
        raise NotImplementedError("Sparse gradient updates are not supported.")
    
    def get_config(self):
        config = super(SGD, self).get_config()
        config.update({
            "learning_rate": self._lr,
            "momentum": self.momentum,
            "manifold": self.manifold
        })
        return config