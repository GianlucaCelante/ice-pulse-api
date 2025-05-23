pipeline {
  agent any

  environment {
    DOCKER_REGISTRY     = 'docker.io/aipioppi'
    INFRA_REPO_URL      = 'git@github.com:GianlucaCelante/ice-pulse-infra.git'
    INFRA_BRANCH        = 'master'
    INFRA_CLONE_DIR     = 'infra'
    DEPLOY_PATH_DEV     = 'devops/dev/ice-pulse-api-deployment.yaml'
    DEPLOY_PATH_STAGING = 'devops/staging/ice-pulse-api-deployment.yaml'
    DEPLOY_PATH_PROD    = 'devops/prod/ice-pulse-api-deployment.yaml'
    CREDENTIALS_GIT     = 'git-creds'
    CREDENTIALS_DOCKER  = 'docker-creds'
    KUBECONFIG_CRED     = 'kubeconfig'
  }

  stages {
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
        sh 'pytest --maxfail=1 --disable-warnings -q'
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
        script {
          docker.withRegistry("https://${DOCKER_REGISTRY}", CREDENTIALS_DOCKER) {
            def img = docker.build("${DOCKER_REGISTRY}/ice-pulse-api:${version}")
            img.push()
          }
        }
      }
    }

    stage('Deploy to Dev') {
      when { branch 'release-dev' }
      steps {
        dir(INFRA_CLONE_DIR) {
          git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
          sh """
            yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_DEV}
            git config user.email "ci@tuo-org.com"
            git config user.name "CI Bot"
            git commit -am "ci: deploy ice-pulse-api:${version} to dev"
            git push origin ${INFRA_BRANCH}
          """
        }
      }
    }

    stage('Promote to Staging') {
      when { branch 'release' }
      steps {
        dir(INFRA_CLONE_DIR) {
          git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
          sh """
            # update manifest
            yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_STAGING}
            # tag for rollback
            git tag staging-v${version}
            git config user.email "ci@tuo-org.com"
            git config user.name "CI Bot"
            git commit -am "ci: deploy ice-pulse-api:${version} to staging"
            git push origin ${INFRA_BRANCH} --tags
          """
        }
      }
    }

    stage('Promote to Prod') {
      when { branch 'release-hv' }
      steps {
        dir(INFRA_CLONE_DIR) {
          git url: INFRA_REPO_URL, branch: INFRA_BRANCH, credentialsId: CREDENTIALS_GIT
          sh """
            yq e -i '.spec.template.spec.containers[0].image = "${DOCKER_REGISTRY}/ice-pulse-api:${version}"' ${DEPLOY_PATH_PROD}
            git tag prod-v${version}
            git config user.email "ci@tuo-org.com"
            git config user.name "CI Bot"
            git commit -am "ci: deploy ice-pulse-api:${version} to prod"
            git push origin ${INFRA_BRANCH} --tags
          """
        }
      }
    }

    stage('Trigger ArgoCD Refresh') {
      when {
        anyOf {
          branch 'release-dev'
          branch 'release'
          branch 'release-hv'
        }
      }
      steps {
        withCredentials([file(credentialsId: KUBECONFIG_CRED, variable: 'KUBECONFIG')]) {
          sh 'kubectl annotate applicationsets.argoproj.io ice-pulse-all-envs -n argocd argocd.argoproj.io/refresh="hard" --overwrite'
        }
      }
    }
  }

  post {
    success {
      echo "Pipeline completed for branch ${env.BRANCH_NAME}"
    }
    failure {
      mail to: 'gianluca.celante@gmail.com',
           subject: "Build failed: ${env.JOB_NAME} [${env.BUILD_NUMBER}]",
           body: "Pipeline fallita su branch ${env.BRANCH_NAME}. Controlla Jenkins."
    }
  }
}
