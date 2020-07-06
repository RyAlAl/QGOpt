from QGOpt.manifolds import base_manifold
import tensorflow as tf
from QGOpt.manifolds.utils import adj
from QGOpt.manifolds.utils import lyap_symmetric


class POVM(base_manifold.Manifold):
    """The manifold of all POVMs of size m.
    POVM is a set of complex positive semi-definite matrices {E_i} for which
    sum_i(E_i) = I, where I is the identity matrix. We use quadratic
    parametrization to represent a particular POVM: E_i = A_i @ adj(A_i).
    Notice that for any unitary matrix Q of size nxn the transformation
    A_i --> A_iQ_i leaves resulting matrix the same. This fact is taken into
    account by consideration of quotient manifold from

    Yatawatta, S. (2013, May). Radio interferometric calibration using a
    Riemannian manifold. In 2013 IEEE International Conference on Acoustics,
    Speech and Signal Processing (pp. 3866-3870). IEEE.

    Args:
        metric: string specifies type of metric, Defaults to 'euclidean'.
            Types of metrics are available: 'euclidean'.

    Notes:
        All methods of this class operates with tensors of shape (..., m, n, n),
        where (...) enumerates manifold (can be any shaped), (m, n, n)
        is the shape of a particular matrix (e.g. an element of the manifold
        or its tangent vector)."""

    def __init__(self, metric='euclidean'):

        self.rank = 3
        list_of_metrics = ['euclidean']

        if metric not in list_of_metrics:
            raise ValueError("Incorrect metric")

    def inner(self, u, vec1, vec2):
        """Returns manifold wise inner product of vectors from
        a tangent space.

        Args:
            u: complex valued tensor of shape (..., m, n, n),
                a set of points from the manifold.
            vec1: complex valued tensor of shape (..., m, n, n),
                a set of tangent vectors from the manifold.
            vec2: complex valued tensor of shape (..., m, n, n),
                a set of tangent vectors from the manifold.

        Returns:
            complex valued tensor of shape (..., 1, 1, 1),
            manifold wise inner product"""

        prod = tf.reduce_sum(tf.math.conj(vec1) * vec2, axis=(-3, -2, -1))
        prod = tf.math.real(prod)
        prod = tf.cast(prod, dtype=u.dtype)[...,
                                            tf.newaxis,
                                            tf.newaxis,
                                            tf.newaxis]
        return prod

    def proj(self, u, vec):
        """Returns projection of vectors on a tangen space
        of the manifold.

        Args:
            u: complex valued tensor of shape (..., m, n, n),
                a set of points from the manifold.
            vec: complex valued tensor of shape (..., m, n, n),
                a set of vectors to be projected.

        Returns:
            complex valued tensor of shape (..., m, n, n),
            a set of projected vectors."""

        n = u.shape[-1]
        m = u.shape[-3]
        shape = u.shape[:-3]
        size = len(shape)
        idx = tuple(range(size))

        # projection onto the tangent space of the Stiefel manifold
        vec_mod = tf.transpose(vec, idx + (size + 2, size, size + 1))
        vec_mod = tf.reshape(vec_mod, shape + (n * m, n))

        u_mod = tf.transpose(u, idx + (size + 2, size, size + 1))
        u_mod = tf.reshape(u_mod, shape + (n * m, n))

        vec_mod = vec_mod - 0.5 * u_mod @ (adj(u_mod) @ vec_mod +\
                                           adj(vec_mod) @ u_mod)
        vec_mod = tf.reshape(vec_mod, shape + (n, m, n))
        vec_mod = tf.transpose(vec_mod, idx + (size + 1, size + 2, size))

        # projection onto the horizontal space (POVM element-wise)
        uu = adj(u) @ u
        Omega = lyap_symmetric(uu, adj(u) @ vec_mod - adj(vec_mod) @ u)
        return vec_mod - u @ Omega

    def egrad_to_rgrad(self, u, egrad):
        """Returns the Riemannian gradient from an Euclidean gradient.

        Args:
            u: complex valued tensor of shape (..., m, n, n),
                a set of points from the manifold.
            egrad: complex valued tensor of shape (..., m, n, n),
                a set of Euclidean gradients.

        Returns:
            complex valued tensor of shape (..., m, n, n),
            the set of Reimannian gradients."""

        n = u.shape[-1]
        m = u.shape[-3]
        shape = u.shape[:-3]
        size = len(shape)
        idx = tuple(range(size))

        # projection onto the tangent space of the Stiefel manifold
        vec_mod = tf.transpose(egrad, idx + (size + 2, size, size + 1))
        vec_mod = tf.reshape(vec_mod, shape + (n * m, n))

        u_mod = tf.transpose(u, idx + (size + 2, size, size + 1))
        u_mod = tf.reshape(u_mod, shape + (n * m, n))

        vec_mod = vec_mod - 0.5 * u_mod @ (adj(u_mod) @ vec_mod +\
                                           adj(vec_mod) @ u_mod)
        vec_mod = tf.reshape(vec_mod, shape + (n, m, n))
        vec_mod = tf.transpose(vec_mod, idx + (size + 1, size + 2, size))

        return vec_mod

    def retraction(self, u, vec):
        """Transports a set of points from the manifold via a
        retraction map.

        Args:
            u: complex valued tensor of shape (..., m, n, n), a set
                of points to be transported.
            vec: complex valued tensor of shape (..., m, n, n),
                a set of direction vectors.

        Returns:
            complex valued tensor of shape (..., m, n, n),
            a set of transported points."""

        n = u.shape[-1]
        m = u.shape[-3]
        shape = u.shape[:-3]
        size = len(shape)
        idx = tuple(range(size))

        # svd based retraction
        u_new = u + vec
        u_new = tf.transpose(u_new, idx + (size + 1, size + 2, size))
        u_new = tf.reshape(u_new, shape + (n, n * m))
        _, U, V = tf.linalg.svd(u_new)

        u_new = U @ adj(V)
        u_new = tf.reshape(u_new, shape + (n, n, m))
        u_new = tf.transpose(u_new, idx + (size + 2, size, size + 1))
        return u_new

    def vector_transport(self, u, vec1, vec2):
        """Returns a vector tranported along an another vector
        via vector transport.

        Args:
            u: complex valued tensor of shape (..., m, n, n),
                a set of points from the manifold, starting points.
            vec1: complex valued tensor of shape (..., m, n, n),
                a set of vectors to be transported.
            vec2: complex valued tensor of shape (..., m, n, n),
                a set of direction vectors.

        Returns:
            complex valued tensor of shape (..., m, n, n),
            a set of transported vectors."""

        u_new = self.retraction(u, vec2)
        return self.proj(u_new, vec1)

    def retraction_transport(self, u, vec1, vec2):
        """Performs a retraction and a vector transport simultaneously.

        Args:
            u: complex valued tensor of shape (..., m, n, n),
                a set of points from the manifold, starting points.
            vec1: complex valued tensor of shape (..., m, n, n),
                a set of vectors to be transported.
            vec2: complex valued tensor of shape (..., m, n, n),
                a set of direction vectors.

        Returns:
            two complex valued tensors of shape (..., m, n, n),
            a set of transported points and vectors."""

        u_new = self.retraction(u, vec2)
        return u_new, self.proj(u_new, vec1)

    def random(self, shape, dtype=tf.complex64):
        """Returns a set of points from the manifold generated
        randomly.

        Args:
            shape: tuple of integer numbers (..., m, n, n),
                shape of a generated matrix.
            dtype: type of an output tensor, can be
                either tf.complex64 or tf.complex128.

        Returns:
            complex valued tensor of shape (..., m, n, n),
            a generated matrix."""

        list_of_dtypes = [tf.complex64, tf.complex128]

        if dtype not in list_of_dtypes:
            raise ValueError("Incorrect dtype")
        real_dtype = tf.float64 if dtype == tf.complex128 else tf.float32

        u = tf.complex(tf.random.normal(shape, dtype=real_dtype),
                       tf.random.normal(shape, dtype=real_dtype))

        n = u.shape[-1]
        m = u.shape[-3]
        shape = u.shape[:-3]

        u = tf.reshape(u, shape + (n * m, n))
        u, _ = tf.linalg.qr(u)
        u = tf.reshape(u, shape + (m, n, n))
        u = tf.linalg.matrix_transpose(u)

        return u

    def random_tangent(self, u):
        """Returns a set of random tangent vectors to points from
        the manifold.

        Args:
            u: complex valued tensor of shape (..., m, n, n), points
                from the manifold.

        Returns:
            complex valued tensor, set of tangent vectors to u."""

        vec = tf.complex(tf.random.normal(u.shape), tf.random.normal(u.shape))
        vec = tf.cast(vec, dtype=u.dtype)
        vec = self.proj(u, vec)
        return vec

    def is_in_manifold(self, u, tol=1e-5):
        """Checks if a point is in the manifold or not.

        Args:
            u: complex valued tensor of shape (..., m, n, n),
                a point to be checked.
            tol: small real value showing tolerance.

        Returns:
            bolean tensor of shape (...)."""

        shape = u.shape[:-3]
        m, n = u.shape[-3], u.shape[-1]
        u_resh = tf.linalg.matrix_transpose(u)
        u_resh = tf.reshape(u_resh, shape + (m * n, n))
        u_resh = tf.linalg.matrix_transpose(u_resh)
        uudag = u_resh @ adj(u_resh)
        Id = tf.eye(uudag.shape[-1], dtype=u.dtype)
        diff = tf.linalg.norm(uudag - Id, axis=(-2, -1))
        uudag_norm = tf.linalg.norm(uudag, axis=(-2, -1))
        Id_norm = tf.linalg.norm(Id, axis=(-2, -1))
        rel_diff = tf.abs(diff / tf.math.sqrt(Id_norm * uudag_norm))
        return tol > rel_diff
