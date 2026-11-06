# Comparación pedagógica de criterios

Placa aislada, inicialmente gaussiana. El equilibrio exacto es uniforme y viene dado por la media ponderada por capacidad y volumen.
Todos los casos calculan el residuo físico completo. La muestra usa un nodo fijo, semilla 1; ΔT compara controles separados por cuatro pasos.
La parada `criterion_met` satisface el criterio elegido, pero no confirma el residuo físico. `max_steps` es límite sin convergencia.

| Caso | Backend | Criterio | Nodos | Pasos | Parada | Error al equilibrio [K] | Residuo [K/s] |
|---|---|---|---|---:|---|---:|---:|
| normal | numpy | residual | all (63) | 80 | converged | 4.2018e-06 | 1.5753e-05 |
| normal | numpy | delta_l1 | all (63) | 100 | converged | 4.1698e-07 | 1.5633e-06 |
| normal | numpy | delta_l1 | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_l2 | all (63) | 88 | converged | 1.6676e-06 | 6.2521e-06 |
| normal | numpy | delta_l2 | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_rms | all (63) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_rms | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_linf | all (63) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_linf | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_matrix_1 | all (63) | 88 | converged | 1.6676e-06 | 6.2521e-06 |
| normal | numpy | delta_matrix_1 | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_matrix_inf | all (63) | 88 | converged | 1.6676e-06 | 6.2521e-06 |
| normal | numpy | delta_matrix_inf | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| normal | numpy | delta_trace | all (7) | 68 | criterion_met | 1.6806e-05 | 6.302e-05 |
| normal | numpy | delta_mean | all (63) | 56 | criterion_met | 6.726e-05 | 0.00025238 |
| normal | numpy | delta_mean | random (1) | 72 | criterion_met | 1.0587e-05 | 3.9697e-05 |
| tiny-dt | numpy | residual | all (63) | 128 | max_steps | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_l1 | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_l1 | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_l2 | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_l2 | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_rms | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_rms | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_linf | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_linf | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_matrix_1 | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_matrix_1 | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_matrix_inf | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_matrix_inf | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_trace | all (7) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_mean | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | numpy | delta_mean | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| normal | opencl | residual | all (63) | 80 | converged | 4.204e-06 | 1.5787e-05 |
| normal | opencl | delta_l1 | all (63) | 100 | converged | 4.1723e-07 | 1.5872e-06 |
| normal | opencl | delta_l1 | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_l2 | all (63) | 88 | converged | 1.6689e-06 | 6.2704e-06 |
| normal | opencl | delta_l2 | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_rms | all (63) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_rms | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_linf | all (63) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_linf | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_matrix_1 | all (63) | 88 | converged | 1.6689e-06 | 6.2704e-06 |
| normal | opencl | delta_matrix_1 | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_matrix_inf | all (63) | 88 | converged | 1.6689e-06 | 6.2704e-06 |
| normal | opencl | delta_matrix_inf | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| normal | opencl | delta_trace | all (7) | 68 | criterion_met | 1.6809e-05 | 6.3018e-05 |
| normal | opencl | delta_mean | all (63) | 56 | criterion_met | 6.726e-05 | 0.00025237 |
| normal | opencl | delta_mean | random (1) | 72 | criterion_met | 1.0589e-05 | 3.971e-05 |
| tiny-dt | opencl | residual | all (63) | 128 | max_steps | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_l1 | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_l1 | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_l2 | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_l2 | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_rms | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_rms | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_linf | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_linf | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_matrix_1 | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_matrix_1 | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_matrix_inf | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_matrix_inf | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_trace | all (7) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_mean | all (63) | 8 | criterion_met | 0.97825 | 27.188 |
| tiny-dt | opencl | delta_mean | random (1) | 8 | criterion_met | 0.97825 | 27.188 |
