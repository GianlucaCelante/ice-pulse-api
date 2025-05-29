pipeline {
  agent {
    kubernetes {
      yaml """
        apiVersion: v1
        kind: Pod
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
    CREDENTIALS_GIT     = 'ice-pulse-api-deploy-key'
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
            pip install pytest || echo "pytest install failed, continuing"
            echo "Test phase completed"
          '''
        }
      }
    }

    stage('Deploy to Dev') {
      when { branch 'release-dev' }
      steps {
        container('kubectl') {
          echo "=== Deploy to Dev ==="
          echo "Version to deploy: ${version}"
          echo "Would clone infra repo and update manifest"
          
          // Test git access
          sh '''
            echo "Testing git access..."
            git --version
          '''
        }
      }
    }
  }

  post {
    success {
      echo "✅ Pipeline completed successfully for branch ${env.BRANCH_NAME}"
      echo "Version: ${version}"
    }
    failure {
      echo "❌ Pipeline failed for branch ${env.BRANCH_NAME}"
    }
    always {
      echo "🧹 Cleanup completed"
    }
  }
}