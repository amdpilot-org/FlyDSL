"""Independent review probe for the actual BM16 inline BF16-to-MXFP4 path."""

import torch

from tests.kernels.test_moe_gemm import _run_mxfp_moe_e2e, build_routing_buffers


def main() -> None:
    device = torch.device("cuda")
    hidden, inter, experts, topk, tile_m = 1024, 256, 8, 4, 16
    for activation in ("silu", "swigluoai"):
        for tokens in (1, 2, 4, 16, 32, 256):
            gen = torch.Generator(device=device).manual_seed(71700 + tokens)
            x = torch.randn((tokens, hidden), generator=gen, device=device) * 0.2
            x[:, :32] = 0.0
            x[:, 32:64:2] = 1.0e-6
            x[:, 33:64:2] = 1.0e3
            x[:, 64:96] = torch.tensor(
                [0.0, -0.0, 0.25, -0.25, 0.5, -0.5, 0.75, -0.75] * 4,
                device=device,
            )
            w1 = torch.randn((experts, 2 * inter, hidden), generator=gen, device=device) * 0.02
            w2 = torch.randn((experts, hidden, inter), generator=gen, device=device) * 0.005
            ids = torch.arange(tokens * topk, device=device).view(tokens, topk) % experts
            ids[:, -1] = ids[:, 0]
            raw = torch.rand((tokens, topk), generator=gen, device=device) + 0.01
            weights = raw / raw.sum(dim=-1, keepdim=True) * 2.0
            routing = build_routing_buffers(
                topk_ids=ids,
                topk_weights=weights,
                experts=experts,
                model_dim=hidden,
                tile_m=tile_m,
                moe_sort_mode="torch",
            )
            out, ref = _run_mxfp_moe_e2e(
                tokens=tokens,
                model_dim=hidden,
                inter_dim=inter,
                experts=experts,
                topk=topk,
                tile_m=tile_m,
                use_reduce=False,
                x_fp32=x,
                w1_fp32=w1,
                w2_fp32=w2,
                topk_ids=ids,
                topk_weights=weights,
                routing=routing,
                inline_quant=True,
                activation=activation,
                swiglu_alpha=1.702,
                swiglu_limit=7.0,
            )
            cosine = torch.nn.functional.cosine_similarity(out.flatten(), ref.flatten(), dim=0).item()
            max_abs = (out - ref).abs().max().item()
            assert torch.isfinite(out).all()
            print(
                f"dispatch=inline-bm16 activation={activation} tokens={tokens} "
                f"cosine={cosine:.8f} max_abs={max_abs:.8f}"
            )


if __name__ == "__main__":
    main()
