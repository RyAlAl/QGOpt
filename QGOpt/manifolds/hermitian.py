import tensorflow as tf
from QGOpt.manifolds import base_manifold
from QGOpt.manifolds.utils import adj


class HermitianMatrix(base_manifold.Manifold):
    """The manifold of Hermitian matrices (the set of complex matrices
    of size nxn for which A = adj(A)).

    Args:
        metric: string specifies type of metric, Defaults to 'euclidean'.
            Types of metrics are available: 'euclidean'.
    """

    def __init__(self, metric='euclidean'):

        list_of_metrics = ['euclidean']

        if metric not in list_of_metrics:
            raise ValueError("Incorrect metric")

    def inner(self, u, vec1, vec2):
        """Returns manifold wise inner product of vectors from
        a tangent space.

        Args:
            u: complex valued tensor of shape (..., n, n),
                a set of points from the manifold.
            vec1: complex valued tensor of shape (..., n, n),
                a set of tangent vectors from the manifold.
            vec2: complex valued tensor of shape (..., n, n),
                a set of tangent vectors from the manifold.

        Returns:
            complex valued tensor of shape (..., 1, 1),
                manifold wise inner product"""

        prod = tf.reduce_sum(tf.math.conj(vec1) * vec2, axis=(-2, -1),
                             keepdims=True)
        prod = tf.cast(tf.math.real(prod), dtype=u.datype)
        return prod

    def proj(self, u, vec):
        """Returns projection of vectors on a tangen space
        of the manifold.

        Args:
            u: complex valued tensor of shape (..., n, n),
                a set of points from the manifold.
            vec: complex valued tensor of shape (..., n, n),
                a set of vectors to be projected.

        Returns:
            complex valued tensor of shape (..., n, n),
            a set of projected vectors"""

        return 0.5 * (vec + adj(vec))

    def egrad_to_rgrad(self, u, egrad):
        """Returns the Riemannian gradient from an Euclidean gradient.

        Args:
            u: complex valued tensor of shape (..., n, n),
                a set of points from the manifold.
            egrad: complex valued tensor of shape (..., n, n),
                a set of Euclidean gradients.

        Returns:
            complex valued tensor of shape (..., n, n),
            the set of Reimannian gradients."""

        return self.proj(u, egrad)

    def retraction(self, u, vec):
        """Transports a set of points from the manifold via a
        retraction map.

        Args:
            u: complex valued tensor of shape (..., n, n), a set
                of points to be transported.
            vec: complex valued tensor of shape (..., n, n),
                a set of direction vectors.

        Returns:
            complex valued tensor of shape (..., n, n),
            a set of transported points."""

        return u + vec

    def vector_transport(self, u, vec1, vec2):
        """Returns a vector tranported along an another vector
        via vector transport.

        Args:
            u: complex valued tensor of shape (..., n, n),
                a set of points from the manifold, starting points.
            vec1: complex valued tensor of shape (..., n, n),
                a set of vectors to be transported.
            vec2: complex valued tensor of shape (..., n, n),
                a set of direction vectors.

        Returns:
            complex valued tensor of shape (..., n, n),
            a set of transported vectors."""

        return vec1

    def retraction_transport(self, u, vec1, vec2):
        """Performs a retraction and a vector transport simultaneously.

        Args:
            u: complex valued tensor of shape (..., n, n),
                a set of points from the manifold, starting points.
            vec1: complex valued tensor of shape (..., n, n),
                a set of vectors to be transported.
            vec2: complex valued tensor of shape (..., n, n),
                a set of direction vectors.

        Returns:
            two complex valued tensors of shape (..., n, n),
            a set of transported points and vectors."""

        new_u = self.retraction(u, vec2)
        return new_u, vec1

    def random(self, shape, dtype=tf.complex64):
        """Returns a set of points from the manifold generated
        randomly.

        Args:
            shape: tuple of integer numbers (..., n, n),
                shape of a generated matrix.
            dtype: type of an output tensor, can be
                either tf.complex64 or tf.complex128.

        Returns:
            complex valued tensor of shape (..., n, n),
            a generated matrix."""

        list_of_dtypes = [tf.complex64, tf.complex128]

        if dtype not in list_of_dtypes:
            raise ValueError("Incorrect dtype")
        real_dtype = tf.float64 if dtype == tf.complex128 else tf.float32

        u = tf.complex(tf.random.normal(shape, dtype=real_dtype),
                       tf.random.normal(shape, dtype=real_dtype))

        u = 0.5 * (u + adj(u))
        return u

    def random_tangent(self, u):
        """Returns a set of random tangent vectors to points from
        the manifold.

        Args:
            u: complex valued tensor of shape (..., n, n), points
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
            u: complex valued tensor of shape (..., n, n),
                a point to be checked.
            tol: small real value showing tolerance.

        Returns:
            bolean tensor of shape (...)."""

        diff_norm = tf.linalg.norm(u - adj(u), axis=(-2, -1))
        u_norm = tf.linalg.norm(u, axis=(-2, -1))
        rel_diff = tf.abs(diff_norm / u_norm)
        return tol > rel_diff