# Entregable 1 - Aplicación en Kubernetes

## Consigna

- En grupos de 2 o 3, pensar en un problema o proyecto a resolver durante el curso.
- Debe desarrollarse una aplicación que será contenerizada y desplegada en Kubernetes.
- Una segunda versión con algún cambio mínimo debe ser desarrollada, y se debe alternar entre despliegues utilizando la estrategia blue/green.

## Condiciones

- Stack de tecnologías libre.
- Alcance acorde al curso.
- Utilización de Dockerfile obligatoria.
- Despliegue en minikube o un cluster a elección.
- Fecha de entrega: semana 5 de clase.

## Evaluación

- Funcionalidad – 30%
- Calidad técnica – 25%
- Uso correcto de k8s – 20%
- Documentación y reproducibilidad – 15%
- Trabajo en equipo – 10%

# Documentación

## Funcionalidad

### Descripción de la Aplicación

La aplicación es una API (API + backend) simple en Python que permite ...

### Endpoints

...

## Stack Tecnológico

La aplicación utiliza:

- [FastAPI](https://fastapi.tiangolo.com/):

    FastAPI es un framework web de alto rendimiento para crear API de servicios basados en HTTP en Python 3.8+. Utiliza Pydantic y sugerencias de tipo para validar, serializar y deserializar datos. FastAPI también genera automáticamente documentación OpenAPI para las API creadas con él.

    > **_Nota_** [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) es una librería de Python que sirve para validar y transformar datos de forma automática.

    > **_Nota_** [OpenAPI](https://www.openapis.org/) es un formato estándar y abierto para describir API REST. Permite definir rutas, parámetros, métodos HTTP y respuestas en archivos legibles por humanos y máquinas usando YAML o JSON, sin importar el lenguaje de programación.

- [Uvicorn](https://uvicorn.dev/):

    Uvicorn es una implementación de servidor web ASGI (Asynchronous Server Gateway Interface) para Python.

    Hasta hace poco, Python carecía de una interfaz de servidor/aplicación de bajo nivel para frameworks asíncronos. La especificación ASGI cubre esta carencia y nos permite comenzar a desarrollar un conjunto común de herramientas utilizables en todos los frameworks asíncronos.

    > **_Nota_** [ASGI (Asynchronous Server Gateway Interface)](https://asgi.readthedocs.io/en/latest/) está diseñado para proporcionar una interfaz estándar entre servidores web, frameworks y aplicaciones Python con capacidad síncrona y asíncrona.

La aplicación es deplegada con:

- [Docker](https://www.docker.com/)

    Docker es una plataforma de código abierto que utiliza la tecnología de contenedores para crear, probar e implementar aplicaciones rápidamente. Empaqueta el software en unidades ligeras e independientes llamadas contenedores, que incluyen todo lo necesario para que la aplicación funcione, como código, entorno de ejecución, herramientas del sistema y bibliotecas. Esto garantiza que la aplicación se comporte de forma idéntica en diferentes entornos, eliminando el clásico problema de "en mi máquina funciona".

- [Kubernetes](https://kubernetes.io/es/)

    Minikube

...

## Archivos

Los archivos de la aplicación son:

- ...

Los archivos para desplegar la aplicación son:

- ...

## Comandos para Desplegar y Utilizar la Aplicación

...