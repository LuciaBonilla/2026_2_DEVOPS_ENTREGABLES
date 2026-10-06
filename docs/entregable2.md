# Entregable 1 - Aplicación en Kubernetes

## Consigna

- Utilizando la aplicacion que crearon para el Entregable 1. Se deberá implementar un sistema de monitoreo y alertas si se pasa determinada cantidad de X operaciones en un período de Y minutos. Ejemplo: si se pasa determinada cantidad de órdenes de un producto en un período de 5 minutos. 
- La solución debe ser contenerizada y desplegada en un cluster de Kubernetes.
- Stack recomendado: Java, Springboot, Prometheus, Grafana

# Documentación

## Funcionalidad de la Aplicación

Ver [Entregable 1](entregable1.md)

## Stack Tecnológico

La aplicación utiliza:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://uvicorn.dev/)

La aplicación es desplegada con:

- [Docker](https://www.docker.com/)
- [Kubernetes (k8s)](https://kubernetes.io/es/)
- [Minikube](https://minikube.sigs.k8s.io/docs/)

El sistema de monitoreo y alertas para la aplicación utiliza:

- Prometheus: recolecta y guarda métricas.
- Grafana: consulta a Prometheus y construye dashboards.

