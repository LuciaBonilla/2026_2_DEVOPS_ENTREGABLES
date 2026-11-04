pipeline {
    agent any

    parameters {
        string(name: 'VERSION', defaultValue: '2.1.1', description: 'Versión de la app (carpeta ci-validator-api/v<VERSION> y tag de la imagen)')
    }

    environment {
        IMAGE   = "ci-validator-api:${params.VERSION}"
        APP_DIR = "ci-validator-api/v${params.VERSION}"
    }

    stages {
        stage('Tests') {
            steps {
                dir(env.APP_DIR) {
                    sh '''
                        python3 -m venv .venv
                        .venv/bin/pip install -q -r requirements-dev.txt
                        .venv/bin/python -m pytest --junitxml=pytest-report.xml
                    '''
                }
            }
            post { always { junit "${env.APP_DIR}/pytest-report.xml" } }
        }

        stage('Build y carga en minikube') {
            steps {
                sh '''
                    docker build -f ci-validator-api/Dockerfile -t "$IMAGE" "$APP_DIR"
                    docker save "$IMAGE" | docker exec -i minikube docker load
                '''
            }
        }

        stage('Deploy') {
            steps { sh 'scripts/deploy.sh' }
        }
    }
}
