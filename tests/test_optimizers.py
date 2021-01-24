import pytest
import tensorflow as tf
import QGOpt.manifolds as manifolds
import QGOpt.optimizers as optimizers
import math

#---------------------------------------------------------------------------------#
ham_dim = 20  # dimension of a hamiltonian
renorm_ham_dim = 10  # dimension of a renormalized hamiltonian
number_of_steps = tf.constant(200, dtype=tf.int32)  # number of optimization steps
#---------------------------------------------------------------------------------#

# hamiltonian generation
herm = manifolds.HermitianMatrix()
h = herm.random((ham_dim, ham_dim), dtype=tf.complex128)

# complex Stiefel manifold
stiefel = manifolds.StiefelManifold()

# initial random isometric matrix
q = stiefel.random((ham_dim, renorm_ham_dim), dtype=tf.complex128)
q = manifolds.complex_to_real(q)
q = tf.Variable(q)

# optimizers
opts = {'GD':optimizers.RSGD(stiefel, 0.05),
        'momentum_GD':optimizers.RSGD(stiefel, 0.1, 0.9),
        'Nesterov_momentum_GD':optimizers.RSGD(stiefel, 0.1, 0.9, use_nesterov=True),
        'Adam':optimizers.RAdam(stiefel, 0.2),
        'AmsGrad':optimizers.RAdam(stiefel, 0.2, ams=True)}

# exact solution of the problem
exact_solution = tf.math.real(tf.reduce_sum(tf.linalg.eigvalsh(h)[:renorm_ham_dim]))

# optimization function
def optimize(q, h, number_of_steps, opt):
    i = tf.constant(0, dtype=tf.int32)
    loss = tf.constant(0, dtype=tf.float64)
    def body(i, loss):
        with tf.GradientTape() as tape:
            qc = manifolds.real_to_complex(q)
            loss = tf.math.real(tf.linalg.trace(tf.linalg.adjoint(qc) @ h @ qc))
        grad = tape.gradient(loss, q)
        opt.apply_gradients(zip([grad], [q]))
        return i + 1, loss
    cond = lambda i, loss: i < number_of_steps
    _, loss = tf.while_loop(cond, body, [i, loss])
    return loss

# optimization loops
err_dict = {}
for key, opt in opts.items():
    loss = optimize(q, h, number_of_steps, opt)
    loss = tf.math.abs(loss - exact_solution)
    assert loss < 1.0e-6, "Optimizer error."
