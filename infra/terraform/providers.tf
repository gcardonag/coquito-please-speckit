provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "coquito"
      Environment = var.environment
    }
  }
}
