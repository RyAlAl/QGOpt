import QGOpt.manifolds as manifolds
import tensorflow as tf


class CheckManifolds():
    def __init__(self, m, descr, shape, tol):
        self.m = m
        self.descr = descr
        self.shape = shape
        self.u = m.random(shape, dtype=tf.complex128)
        self.v1 = m.random_tangent(self.u)
        self.v2 = m.random_tangent(self.u)
        self.zero = self.u * 0.
        self.tol = tol

    def _proj_of_tangent(self):
        """
        Checking m.proj: Projection of a vector from a tangent space
        does't shange the vector
        Args:

        Returns:
            error, dtype float32
        """
        return tf.reduce_mean(tf.abs(self.v1 - self.m.proj(self.u, self.v1)))

    def _inner_proj_matching(self):
        """
        Checking m.inner and m.proj
        arXiv:1906.10436v1: proj_ksi = argmin(-inner(z,ksi)+0.5inner(ksi,ksi))

        Args:

        Returns:
            error, number of False counts, dtype int
        """
        xi = tf.complex(tf.random.normal(self.shape),
                        tf.random.normal(self.shape))
        xi = tf.cast(xi, dtype=self.u.dtype)

        xi_proj = self.m.proj(self.u, xi)
        with tf.GradientTape() as tape:
            tape.watch(xi_proj)
            loss_min = -self.m.inner(self.u, xi, xi_proj) + 0.5 * self.m.inner(
                                            self.u, xi_proj, xi_proj)
            loss_min = tf.math.real(loss_min)
        grad = tape.gradient(loss_min, xi_proj)
        grad_proj = self.m.proj(self.u, grad)
        err = tf.linalg.norm(grad_proj, axis=(-2, -1))
        return tf.math.real(err)

    def _retraction(self):
        """
        Checking retraction
        Page 46, Nikolas Boumal, An introduction to optimization on smooth
        manifolds
        1) Rx(0) = x (Identity mapping)
        2) DRx(o)[v] = v : introduce v->t*v, calculate err=dRx(tv)/dt|_{t=0}-v
        Args:

        Returns:
            error 1), dtype float32
            error 2), dtype float32
            error 3), dtype boolean
        """
        dt = 1e-8

        err1 = self.u - self.m.retraction(self.u, self.zero)
        err1 = tf.math.real(tf.linalg.norm(err1))

        t = tf.constant(dt, dtype=self.u.dtype)
        retr = self.m.retraction(self.u, t * self.v1)
        dretr = (retr - self.u) / dt
        err2 = tf.linalg.norm(dretr - self.v1)

        err3 = self.m.is_in_manifold(self.m.retraction(self.u, self.v1))
        return err1, err2, err3  # err3 has boolean type

    def _vector_transport(self):
        """
        Checking vector transport.
        Page 264, Nikolas Boumal, An introduction to optimization on smooth
        manifolds
        1) transported v2 in a tangent space
        2) VT(x,0)[v] is the identity on TxM.
        Args:

        Returns:
            error 1), dtype float32
            error 2), dtype float32
        """
        VT = self.m.vector_transport(self.u, self.v1, self.v2)
        err1 = VT - self.m.proj(self.m.retraction(self.u, self.v2), VT)
        err1 = tf.reduce_mean(tf.abs(err1))

        err2 = self.v1 - self.m.vector_transport(self.u, self.v1, self.zero)
        err2 = tf.reduce_mean(tf.abs(err2))
        return err1, err2

    def _egrad_to_rgrad(self):
        """
        Checking egrad to rgrad.
        1) rgrad is in a tangent space
        2) <v1 egrad> = inner<v1 rgrad>
        Args:

        Returns:
            error 1), dtype float32
            error 2), dtype float32
        """

        proj = self.m.egrad_to_rgrad(self.u, self.v1)
        err1 = proj - self.m.proj(self.u, proj)
        err1 = tf.reduce_mean(tf.abs(err1))

        err2 = tf.reduce_sum(tf.math.conj(self.v1) * self.v1, axis=(-2, -1)) -\
                        self.m.inner(self.u, self.v1,
                        self.m.egrad_to_rgrad(self.u, self.v1))
        err2 = tf.math.real(err2)
        return err1, err2

    def checks(self):
        """ TODO after checking: rewrite with asserts!!!
        Routine for pytest: checking tolerance of manifold functions
        """
        err = self._proj_of_tangent()
        if err > self.tol:
            print("Projection error for:{}. Error {} >\
            tol {}".format(self.descr, err, self.tol))

        err = self._inner_projection()
        if err > self.tol:
            print("Inner error for:{}. Error {} >\
            tol {}".format(self.descr, err, self.tol))

        err1, err2 = self._retraction()
        if err1 > self.tol:
            print("Retraction (Rx(0) != x) error for:{}. Error {} >\
            tol {}".format(self.descr, err1, self.tol))
        if err2 > self.tol:
            print("Retraction (DRx(o)[v] != v) error for:{}. Error {} >\
            tol {}".format(self.descr, err2, self.tol))

        err1, err2 = self._vector_transpot()
        if err1 > self.tol:
            print("Vector transport (not in a TMx) error for:{}. Error {} >\
            tol {}".format(self.descr, err1, self.tol))
        if err2 > self.tol:
            print("Vector transport (VT(x,0)[v] != v) error for:{}. Error {} >\
            tol {}".format(self.descr, err2, self.tol))

        err1, err2 = self._egrad_to_rgrad()
        if err1 > self.tol:
            print("Rgrad (not in a TMx) error for:{}. Error {} >\
            tol {}".format(self.descr, err1, self.tol))
        if err2 > self.tol:
            print("Rgrad (<v1 egrad> != inner<v1 rgrad>) error for:{}. \
            Error {} > tol {}".format(self.descr, err2, self.tol))


def return_manifold(name):
    """
    Returns a list of possible manifolds with name 'name'.
    Args:
        name: manifold name, str.
    Returns:
        list of manifolds, name, metrics, retractions
    """
    m_list = []
    descr_list = []
    if name == 'ChoiMatrix':
        list_of_metrics = ['euclidean']
        for metric in list_of_metrics:
            m_list.append(manifolds.ChoiMatrix(metric=metric))
            descr_list.append((name, metric))
    if name == 'DensityMatrix':
        list_of_metrics = ['euclidean']
        for metric in list_of_metrics:
            m_list.append(manifolds.DensityMatrix(metric=metric))
            descr_list.append((name, metric))
    if name == 'HermitianMatrix':
        list_of_metrics = ['euclidean']
        for metric in list_of_metrics:
            m_list.append(manifolds.HermitianMatrix(metric=metric))
            descr_list.append((name, metric))
    if name == 'PositiveCone':
        list_of_metrics = ['log_euclidean', 'log_cholesky']
        for metric in list_of_metrics:
            m_list.append(manifolds.PositiveCone(metric=metric))
            descr_list.append((name, metric))
    if name == 'StiefelManifold':
        list_of_metrics = ['euclidean', 'canonical']
        list_of_retractions = ['svd', 'cayley', 'qr']
        for metric in list_of_metrics:
            for retraction in list_of_retractions:
                m_list.append(manifolds.StiefelManifold(metric=metric,
                                                    retraction=retraction))
                descr_list.append((name, metric, retraction))
    return m_list, descr_list


def test_manifolds(shape=(4,4), tol=0.0001):
    """
    Pytest runs tests function for all implemented manifolds and checks asserts.
    Args:
        shape in the form (n,n) - size of a manifold point
    Returns:
        errors in Pytest format
    """
    list_of_manifolds = ['ChoiMatrix', 'DensityMatrix', 'HermitianMatrix',
                        'PositiveCone', 'StiefelManifold']

    for name in list_of_manifolds:
        m_list, descr_list = return_manifold(name)
        for _, (m, descr) in enumerate(zip(m_list, descr_list)):
            Test = CheckManifolds(m, descr, shape, tol)
            #Test.checks()
            print(Test.checks(), descr)
            print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')

test_manifolds()