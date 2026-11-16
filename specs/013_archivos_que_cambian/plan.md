# 013 · Plan

## Enfoque

- `Historial.de_ruta(ruta)` devuelve `(id, tamaño)` de lo anotado en esa ruta (índice inverso
  que se arma una vez por corrida y se mantiene al anotar).
- En `sincronizar._decidir()`, si `Indice.buscar()` responde «mismo nombre» y en esa ruta el
  historial tiene **otro id** con un tamaño conocido y distinto del que trae Canvas, el archivo no
  se da por tenido: se baja a su carpeta de siempre con el primer nombre libre `Nombre (vN).ext`
  (N ≥ 2), reservado en el índice. Si la carpeta de destino no tiene ese nombre, va con el nombre
  original (otro archivo de otra semana con el mismo nombre).
- `_mover()` ya se niega a pisar: si el nombre se ocupó mientras bajaba, no se guarda.

## Principios

- P4: solo crea. Nada se pisa ni se renombra.
- P2: no hay pedidos nuevos; todo sale de la fase «consultas» y del historial.
