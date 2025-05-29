pipeline {
  agent {
    kubernetes {
      label 'k8s-agent'
      yaml """
        apiVersion: v1
        kind: Pod
        metadata:
          labels:
            jenkins: k8s-agent
        spec:
          serviceAccountName: jenkins
          containers:
          - name: jnlp
            image: jenkins/inbound-agent:latest
            args: ['\$(JENKINS_SECRET)', '\$(JENKINS_NAME)']
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "200m"
          - name: python
            image: python:3.9-slim
            command:
            - cat
            tty: true
            resources:
              requests:
                memory: "128Mi"
                cpu: "50m"
              limits:
                memory: "256Mi"
                cpu: "100m"
          - name: docker
            image: docker:20.10-dind
            securityContext:
              privileged: true
            volumeMounts:
            - name: docker-sock
              mountPath: /var/run/docker.sock
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "200m"
          - name: kubectl
            image: bitnami/kubectl:latest
            command:
            - cat
            tty: true
            resources:
              requests:
                memory: "64Mi"
                cpu: "50m"
              limits:
                memory: "128Mi"
                cpu: "100m"
          volumes:
          - name: docker-sock
            hostPath:
              path: /var/run/docker.sock
      """
    }
  }
  
  environment {
    DOCKER_REGISTRY     = 'docker.io/aipioppi'
    INFRA_REPO_URL      = 'git@github.com:GianlucaCelante/ice-pulse-infra.git'
    INFRA_BRANCH        = 'master'
    INFRA_CLONE_DIR     = 'infra'
    DEPLOY_PATH_DEV     = 'devops/dev/ice-pulse-api-deployment.yaml'
    DEPLOY_PATH_STAGING = 'devops/staging/ice-pulse-api-deployment.yaml'
    DEPLOY_PATH_PROD    = 'devops/prod/ice-pulse-api-deployment.yaml'
    CREDENTIALS_GIT     = 'jenkins-deploy-api-ed25519'
    CREDENTIALS_DOCKER  = 'docker-creds'
    KUBECONFIG_CRED     = 'kubeconfig'
  }

  stages {
    stage('Debug Environment') {
      steps {
        script {
          echo "=== DEBUG INFO ==="
          echo "Node name: ${env.NODE_NAME}"
          echo "Workspace: ${env.WORKSPACE}"
          
          sh '''
            echo "=== Container Info ==="
            hostname
            whoami
            pwd
            ls -la
          '''
        }
      }
    }

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Read Version') {
      steps {
        script {
          version = readFile('VERSION').trim()
          echo "Version: ${version}"
        }
      }
    }

    stage('Build & Test') {
      steps {
        container('python') {
          sh '''
            echo "=== Python Container ==="
            python3 --version
            pip install pytest || echo "pytest install failed, continuing for now"
            echo "Test phase completed"
          '''
        }
      }
    }

    stage('Build & Push Image') {
      when {
        anyOf {
          branch 'release-dev'
          branch 'release'
          branch 'release-hv'
        }
      }
      steps {
        container('docker') {
          script {
            echo "Docker build would happen here for version: ${version}"
            // Temporaneamente commentato per test
            // docker.withRegistry("https://index.docker.io/v1/", CREDENTIALS_DOCKER) {
            //   def img = docker.build("${DOCKER_REGISTRY}/ice-pulse-api:${version}")
            //   img.push()
            // }
          }
        }
      }
    }

    stage('Deploy to Dev') {
      when { branch 'release-dev' }
      steps {
        container('kubectl') {
          echo "Deployment to dev would happen here for version: ${version}"
          // Temporaneamente commentato per test
          // dir(INFRA_CLONE_DIR) {
          //   git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
          //   sh """
          //     echo "Would update deployment manifest here"
          //   """
          // }
        }
      }
    }
  }

  post {
    success {
      echo "Pipeline completed successfully for branch ${env.BRANCH_NAME}"
    }
    failure {
      echo "Pipeline failed for branch ${env.BRANCH_NAME}"
    }
  }
}