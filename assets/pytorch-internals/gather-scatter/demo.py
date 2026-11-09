"""Two-dimensional gather/scatter examples. Run with PyTorch 2.8+ on CPU."""

import torch
from torch.autograd import gradcheck


def gather_columns():
    x = torch.tensor([[10., 20., 30., 40.],
                      [50., 60., 70., 80.]])
    index = torch.tensor([[2, 0, 2],
                          [1, 3, 0]], dtype=torch.long)
    out = x.gather(dim=1, index=index)
    # out = [[30, 10, 30],
    #        [60, 80, 50]]
    return x, index, out


def gather_rows():
    x = torch.tensor([[10., 20., 30., 40.],
                      [50., 60., 70., 80.]])
    index = torch.tensor([[1, 0, 1, 0],
                          [0, 1, 1, 0],
                          [1, 1, 0, 1]], dtype=torch.long)
    out = x.gather(dim=0, index=index)
    # out = [[50, 20, 70, 40],
    #        [10, 60, 70, 40],
    #        [50, 60, 30, 80]]
    return x, index, out


def scatter_columns():
    base = torch.tensor([[1., 2., 3., 4.],
                         [5., 6., 7., 8.]])
    src = torch.tensor([[10., 20., 30.],
                        [40., 50., 60.]])
    index = torch.tensor([[2, 0, 3],
                          [1, 3, 0]], dtype=torch.long)
    out = base.scatter(dim=1, index=index, src=src)
    # out = [[20,  2, 10, 30],
    #        [60, 40,  7, 50]]
    # base is unchanged.
    return base, src, index, out


def scatter_rows():
    base = torch.zeros(3, 4)
    src = torch.tensor([[10., 20., 30., 40.],
                        [50., 60., 70., 80.]])
    index = torch.tensor([[2, 0, 1, 0],
                          [0, 2, 0, 1]], dtype=torch.long)
    out = base.scatter(dim=0, index=index, src=src)
    # out = [[50, 20, 70, 40],
    #        [ 0,  0, 30, 80],
    #        [10, 60,  0,  0]]
    return base, src, index, out


def gather_backward():
    x = torch.tensor([[10., 20., 30., 40.],
                      [50., 60., 70., 80.]], requires_grad=True)
    index = torch.tensor([[2, 0, 2], [1, 3, 0]])
    out = x.gather(1, index)
    g = torch.tensor([[1., 2., 3.], [4., 5., 6.]])
    loss = (out * g).sum()  # d(loss)/d(out) = g
    (dx,) = torch.autograd.grad(loss, (x,))
    expected_dx = torch.zeros_like(x).scatter_add(1, index, g)
    # dx = [[2, 0, 4, 0],
    #       [6, 4, 0, 5]]
    return dx, expected_dx


def scatter_backward():
    base = torch.tensor([[1., 2., 3., 4.],
                         [5., 6., 7., 8.]], requires_grad=True)
    src = torch.tensor([[10., 20., 30.],
                        [40., 50., 60.]], requires_grad=True)
    index = torch.tensor([[2, 0, 3], [1, 3, 0]])
    out = base.scatter(1, index, src)
    g = torch.tensor([[1., 2., 3., 4.], [5., 6., 7., 8.]])
    dbase, dsrc = torch.autograd.grad((out * g).sum(), (base, src))
    expected_dbase = g.scatter(1, index, 0.)
    expected_dsrc = g.gather(1, index)
    # dbase = [[0, 2, 0, 0], [0, 0, 7, 0]]
    # dsrc  = [[3, 1, 4],    [6, 8, 5]]
    return dbase, dsrc, expected_dbase, expected_dsrc


def scatter_add_backward():
    base = torch.tensor([[1., 2., 3., 4.],
                         [5., 6., 7., 8.]], requires_grad=True)
    src = torch.tensor([[10., 20., 30.],
                        [40., 50., 60.]], requires_grad=True)
    index = torch.tensor([[2, 0, 2], [1, 3, 0]])
    out = base.scatter_add(1, index, src)
    g = torch.tensor([[1., 2., 3., 4.], [5., 6., 7., 8.]])
    dbase, dsrc = torch.autograd.grad((out * g).sum(), (base, src))
    # out   = [[21,  2, 43,  4], [65, 46, 7, 58]]
    # dbase = [[ 1,  2,  3,  4], [ 5,  6, 7,  8]]
    # dsrc  = [[ 3,  1,  3],     [ 6,  8, 5]]
    return out, dbase, dsrc, g, g.gather(1, index)


def batch_lookup():
    features = torch.arange(2 * 4 * 3, dtype=torch.float32).reshape(2, 4, 3)
    ids = torch.tensor([[2, 0], [1, 3]])  # [B, K]
    index = ids.unsqueeze(-1).expand(-1, -1, features.size(-1))
    selected = features.gather(1, index)  # [B, K, D] = [2, 2, 3]
    # selected = [[[ 6,  7,  8], [ 0,  1,  2]],
    #             [[15, 16, 17], [21, 22, 23]]]
    return features, ids, selected


def verify():
    torch.manual_seed(7)
    close = torch.testing.assert_close
    close(gather_columns()[-1], torch.tensor([[30., 10., 30.], [60., 80., 50.]]))
    close(gather_rows()[-1], torch.tensor([[50., 20., 70., 40.],
                                         [10., 60., 70., 40.],
                                         [50., 60., 30., 80.]]))
    base, _, _, out = scatter_columns()
    close(out, torch.tensor([[20., 2., 10., 30.], [60., 40., 7., 50.]]))
    close(base, torch.tensor([[1., 2., 3., 4.], [5., 6., 7., 8.]]))
    close(scatter_rows()[-1], torch.tensor([[50., 20., 70., 40.],
                                          [0., 0., 30., 80.],
                                          [10., 60., 0., 0.]]))
    dx, expected = gather_backward()
    close(dx, expected)
    close(dx, torch.tensor([[2., 0., 4., 0.], [6., 4., 0., 5.]]))
    db, ds, expected_db, expected_ds = scatter_backward()
    close(db, expected_db)
    close(ds, expected_ds)
    close(db, torch.tensor([[0., 2., 0., 0.], [0., 0., 7., 0.]]))
    close(ds, torch.tensor([[3., 1., 4.], [6., 8., 5.]]))
    out, db, ds, expected_db, expected_ds = scatter_add_backward()
    close(out, torch.tensor([[21., 2., 43., 4.], [65., 46., 7., 58.]]))
    close(db, expected_db)
    close(ds, expected_ds)
    _, _, selected = batch_lookup()
    close(selected, torch.tensor([[[6., 7., 8.], [0., 1., 2.]],
                                  [[15., 16., 17.], [21., 22., 23.]]]))

    # Independent numerical Jacobian checks for both axes, including duplicates.
    repeated = torch.tensor([[2, 0, 2], [1, 3, 0]])
    unique = torch.tensor([[2, 0, 3], [1, 3, 0]])
    for dim in (0, 1):
        index = repeated if dim == 1 else repeated.T.contiguous()
        distinct = unique if dim == 1 else unique.T.contiguous()
        shape = (2, 4) if dim == 1 else (4, 2)
        x = torch.randn(shape, dtype=torch.double, requires_grad=True)
        src = torch.randn(index.shape, dtype=torch.double, requires_grad=True)
        assert gradcheck(lambda a: a.gather(dim, index), (x,))
        assert gradcheck(lambda a, s: a.scatter(dim, distinct, s), (x, src))
        assert gradcheck(lambda a, s: a.scatter_add(dim, index, s), (x, src))

        g = torch.randn(index.shape, dtype=torch.double)
        (dx,) = torch.autograd.grad(x.gather(dim, index), x, g)
        close(dx, torch.zeros_like(x).scatter_add(dim, index, g))
        sparse_x = x.detach().requires_grad_()
        (sparse_dx,) = torch.autograd.grad(
            sparse_x.gather(dim, index, sparse_grad=True), sparse_x, g)
        assert sparse_dx.is_sparse
        close(sparse_dx.coalesce().to_dense(), dx)

    # A repeated overwrite has no portable winner; the VJP is still sent to both.
    source = torch.tensor([[10., 20., 30.]], requires_grad=True)
    index = torch.tensor([[2, 0, 2]])
    collision = torch.zeros(1, 4).scatter(1, index, source)
    upstream = torch.tensor([[1., 2., 3., 4.]])
    (reported,) = torch.autograd.grad(collision, source, upstream)
    close(reported, torch.tensor([[3., 1., 3.]]))
    assert collision[0, 2].item() in (10., 30.)

    # Forward shape support is broader than the documented backward contract.
    larger = torch.arange(8., requires_grad=True).reshape(2, 4)
    result = torch.zeros(2, 4).scatter(1, unique, larger)
    close(result, torch.tensor([[1., 0., 0., 2.], [6., 4., 0., 5.]]))
    try:
        torch.autograd.grad(result.sum(), larger)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Expected src/index shape mismatch during backward')
    print(f'PASS: forward values, VJPs, both axes, sparse gradients, and 6 gradchecks; torch={torch.__version__}')


if __name__ == '__main__':
    verify()
