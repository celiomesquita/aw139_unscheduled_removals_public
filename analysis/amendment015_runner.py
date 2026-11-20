"""Entry point for the isolated amendment 015 reference block."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'

if __name__=='__main__':
    import traceback
    from amendment015.state import ledger
    # Start before loading scientific dependencies or any reference inputs.
    ledger('reference_preparation',begin_references=True)
    from amendment015.references import calculate,stop_state
    try:
        calculate()
    except Exception as error:
        stop_state(error)
        traceback.print_exc()
        raise SystemExit(1)
