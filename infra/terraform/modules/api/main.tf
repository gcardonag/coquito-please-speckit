locals {
  lambda_runtime        = "python3.12"
  lambda_zip            = var.lambda_zip_path
  lambda_handler_prefix = "src.handlers"
  lambda_architectures  = ["arm64"]
}

# ---------------------------------------------------------------------------
# Lambda Layer — Python dependencies (arm64, Amazon Linux 2023)
# ---------------------------------------------------------------------------
resource "aws_lambda_layer_version" "deps" {
  layer_name               = "coquito-deps-${var.environment}"
  filename                 = var.lambda_layer_zip_path
  source_code_hash         = filebase64sha256(var.lambda_layer_zip_path)
  compatible_runtimes      = ["python3.12"]
  compatible_architectures = ["arm64"]
}

# ---------------------------------------------------------------------------
# HTTP API v2
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "main" {
  name          = "coquito-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins     = ["https://${var.domain}"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["Content-Type", "Cookie"]
    allow_credentials = true
    max_age           = 86400
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# ---------------------------------------------------------------------------
# Lambda Authorizer
# ---------------------------------------------------------------------------
resource "aws_iam_role" "lambda_exec" {
  name = "coquito-lambda-exec-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_ssm" {
  name = "coquito-lambda-ssm-${var.environment}"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:*:*:parameter/coquito/${var.environment}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_cognito" {
  name = "coquito-lambda-cognito-${var.environment}"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminAddUserToGroup",
        ]
        Resource = var.cognito_user_pool_arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "coquito-lambda-dynamodb-${var.environment}"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
        ]
        Resource = "arn:aws:dynamodb:*:*:table/coquito-*"
      }
    ]
  })
}

resource "aws_lambda_function" "authorizer" {
  function_name = "coquito-auth-authorizer"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.auth.authorizer.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      COGNITO_USER_POOL_ID = var.cognito_user_pool_id
      COGNITO_CLIENT_ID    = var.cognito_client_id
      JWKS_URI             = var.cognito_jwks_uri
      ENVIRONMENT          = var.environment
    }
  }
}

resource "aws_apigatewayv2_authorizer" "main" {
  api_id                            = aws_apigatewayv2_api.main.id
  authorizer_type                   = "REQUEST"
  authorizer_uri                    = aws_lambda_function.authorizer.invoke_arn
  name                              = "coquito-jwt-authorizer"
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  authorizer_result_ttl_in_seconds  = 300
  identity_sources                  = ["$request.header.Cookie"]
}

resource "aws_lambda_permission" "authorizer" {
  statement_id  = "AllowAPIGatewayInvokeAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Lambda functions — auth (public, no authorizer)
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "auth_token_exchange" {
  function_name = "coquito-auth-token-exchange"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.auth.token_exchange.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 15
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      COGNITO_CLIENT_ID = var.cognito_client_id
      SSM_CLIENT_SECRET = var.cognito_client_secret_ssm_path
      TOKEN_ENDPOINT    = var.cognito_token_endpoint
      REDIRECT_URI      = "https://${var.domain}/auth/callback"
      ENVIRONMENT       = var.environment
    }
  }
}

resource "aws_lambda_function" "auth_logout" {
  function_name = "coquito-auth-logout"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.auth.logout.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      COGNITO_CLIENT_ID = var.cognito_client_id
      SSM_CLIENT_SECRET = var.cognito_client_secret_ssm_path
      TOKEN_ENDPOINT    = var.cognito_token_endpoint
      ENVIRONMENT       = var.environment
    }
  }
}

resource "aws_lambda_function" "auth_refresh" {
  function_name = "coquito-auth-refresh"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.auth.refresh.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]

  environment {
    variables = {
      COGNITO_CLIENT_ID = var.cognito_client_id
      SSM_CLIENT_SECRET = var.cognito_client_secret_ssm_path
      TOKEN_ENDPOINT    = var.cognito_token_endpoint
      ENVIRONMENT       = var.environment
    }
  }
}

# ---------------------------------------------------------------------------
# Lambda functions — existing handlers (protected)
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "health" {
  function_name = "coquito-health"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.health.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "list_varieties" {
  function_name = "coquito-list-varieties"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.list_varieties.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT                = var.environment
      DYNAMODB_REQUESTS_TABLE    = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE     = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE   = var.dynamodb_varieties_table
      CLOUDFRONT_ASSETS_BASE_URL = var.cloudfront_assets_base_url
    }
  }
}

resource "aws_lambda_function" "create_request" {
  function_name = "coquito-create-request"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.create_request.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "get_request" {
  function_name = "coquito-get-request"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.get_request.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "update_request" {
  function_name = "coquito-update-request"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.update_request.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "cancel_request" {
  function_name = "coquito-cancel-request"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.cancel_request.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "get_batch_config" {
  function_name = "coquito-get-batch-config"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.get_batch_config.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "get_ingredient_list" {
  function_name = "coquito-get-ingredient-list"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.get_ingredient_list.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "mark_ingredient_acquired" {
  function_name = "coquito-mark-ingredient-acquired"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.mark_ingredient_acquired.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "send_reminder" {
  function_name = "coquito-send-reminder"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.send_reminder.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "create_user" {
  function_name = "coquito-create-user"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = local.lambda_runtime
  handler       = "${local.lambda_handler_prefix}.create_user.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout       = 10
  architectures = local.lambda_architectures
  layers        = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      COGNITO_USER_POOL_ID     = var.cognito_user_pool_id
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

# ---------------------------------------------------------------------------
# Lambda permissions — API Gateway invoke
# ---------------------------------------------------------------------------
locals {
  protected_functions = {
    health                   = aws_lambda_function.health
    list_varieties           = aws_lambda_function.list_varieties
    create_request           = aws_lambda_function.create_request
    get_request              = aws_lambda_function.get_request
    update_request           = aws_lambda_function.update_request
    cancel_request           = aws_lambda_function.cancel_request
    get_batch_config         = aws_lambda_function.get_batch_config
    get_ingredient_list      = aws_lambda_function.get_ingredient_list
    mark_ingredient_acquired = aws_lambda_function.mark_ingredient_acquired
    send_reminder            = aws_lambda_function.send_reminder
    create_user              = aws_lambda_function.create_user
    get_me                   = aws_lambda_function.get_me
    list_batches             = aws_lambda_function.list_batches
    create_batch             = aws_lambda_function.create_batch
    update_batch             = aws_lambda_function.update_batch
    update_batch_status      = aws_lambda_function.update_batch_status
    chef_list_varieties      = aws_lambda_function.chef_list_varieties
    chef_create_variety      = aws_lambda_function.chef_create_variety
    chef_update_variety      = aws_lambda_function.chef_update_variety
  }
  public_functions = {
    auth_token_exchange = aws_lambda_function.auth_token_exchange
    auth_logout         = aws_lambda_function.auth_logout
    auth_refresh        = aws_lambda_function.auth_refresh
  }
}

resource "aws_lambda_permission" "protected" {
  for_each      = local.protected_functions
  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "public" {
  for_each      = local.public_functions
  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_integration" "health" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.health.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "list_varieties" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.list_varieties.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "create_request" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_request.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_request" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_request.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "update_request" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.update_request.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "cancel_request" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.cancel_request.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_batch_config" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_batch_config.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_ingredient_list" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_ingredient_list.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "mark_ingredient_acquired" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.mark_ingredient_acquired.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "send_reminder" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.send_reminder.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "auth_token_exchange" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.auth_token_exchange.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "auth_logout" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.auth_logout.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "auth_refresh" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.auth_refresh.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "create_user" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_user.invoke_arn
  payload_format_version = "2.0"
}

# ---------------------------------------------------------------------------
# Routes — public (no authorizer)
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.health.id}"
}

resource "aws_apigatewayv2_route" "auth_callback" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/callback"
  target    = "integrations/${aws_apigatewayv2_integration.auth_token_exchange.id}"
}

resource "aws_apigatewayv2_route" "auth_logout" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/logout"
  target    = "integrations/${aws_apigatewayv2_integration.auth_logout.id}"
}

resource "aws_apigatewayv2_route" "auth_refresh" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/refresh"
  target    = "integrations/${aws_apigatewayv2_integration.auth_refresh.id}"
}

# ---------------------------------------------------------------------------
# Routes — protected (Lambda authorizer)
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_route" "list_varieties" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/varieties"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.list_varieties.id}"
}

resource "aws_apigatewayv2_route" "create_request" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/requests"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.create_request.id}"
}

resource "aws_apigatewayv2_route" "get_request" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/requests/{id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.get_request.id}"
}

resource "aws_apigatewayv2_route" "update_request" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /api/v1/requests/{id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.update_request.id}"
}

resource "aws_apigatewayv2_route" "cancel_request" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/requests/{id}/cancel"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.cancel_request.id}"
}

resource "aws_apigatewayv2_route" "get_batch_config" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/batches/{id}/config"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.get_batch_config.id}"
}

resource "aws_apigatewayv2_route" "get_ingredient_list" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/batches/{id}/ingredients"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.get_ingredient_list.id}"
}

resource "aws_apigatewayv2_route" "mark_ingredient_acquired" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /api/v1/batches/{id}/ingredients/{ingredId}/acquired"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.mark_ingredient_acquired.id}"
}

resource "aws_apigatewayv2_route" "send_reminder" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/requests/{id}/reminder"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.send_reminder.id}"
}

resource "aws_apigatewayv2_route" "create_user" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/users"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.create_user.id}"
}

# ---------------------------------------------------------------------------
# Custom domain
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_domain_name" "main" {
  domain_name = "api.${var.domain}"

  domain_name_configuration {
    certificate_arn = var.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.main.id
  stage       = aws_apigatewayv2_stage.default.id
}

# ---------------------------------------------------------------------------
# CloudWatch log groups (retention: 30 days, T057)
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "authorizer" {
  name              = "/aws/lambda/coquito-auth-authorizer"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "auth_token_exchange" {
  name              = "/aws/lambda/coquito-auth-token-exchange"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "auth_logout" {
  name              = "/aws/lambda/coquito-auth-logout"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "auth_refresh" {
  name              = "/aws/lambda/coquito-auth-refresh"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "health" {
  name              = "/aws/lambda/coquito-health"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "list_varieties" {
  name              = "/aws/lambda/coquito-list-varieties"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "create_request" {
  name              = "/aws/lambda/coquito-create-request"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "get_request" {
  name              = "/aws/lambda/coquito-get-request"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "update_request" {
  name              = "/aws/lambda/coquito-update-request"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "cancel_request" {
  name              = "/aws/lambda/coquito-cancel-request"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "get_batch_config" {
  name              = "/aws/lambda/coquito-get-batch-config"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "get_ingredient_list" {
  name              = "/aws/lambda/coquito-get-ingredient-list"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "mark_ingredient_acquired" {
  name              = "/aws/lambda/coquito-mark-ingredient-acquired"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "send_reminder" {
  name              = "/aws/lambda/coquito-send-reminder"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "create_user" {
  name              = "/aws/lambda/coquito-create-user"
  retention_in_days = 30
}

# ---------------------------------------------------------------------------
# Lambda functions — chef batch management (protected, chef-role required)
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "get_me" {
  function_name    = "coquito-get-me"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.get_me.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "list_batches" {
  function_name    = "coquito-list-batches"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.list_batches.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "create_batch" {
  function_name    = "coquito-create-batch"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.create_batch.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "update_batch" {
  function_name    = "coquito-update-batch"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.update_batch.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "update_batch_status" {
  function_name    = "coquito-update-batch-status"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.update_batch_status.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "close_expired_batches" {
  function_name    = "coquito-close-expired-batches"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.close_expired_batches.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 60
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

# ---------------------------------------------------------------------------
# Integrations — chef batch management
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_integration" "get_me" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_me.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "list_batches" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.list_batches.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "create_batch" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_batch.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "update_batch" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.update_batch.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "update_batch_status" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.update_batch_status.invoke_arn
  payload_format_version = "2.0"
}

# ---------------------------------------------------------------------------
# Routes — chef batch management (protected, Lambda authorizer)
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_route" "get_me" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/me"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.get_me.id}"
}

resource "aws_apigatewayv2_route" "list_batches" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/batches"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.list_batches.id}"
}

resource "aws_apigatewayv2_route" "create_batch" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/batches"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.create_batch.id}"
}

resource "aws_apigatewayv2_route" "update_batch" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /api/v1/batches/{id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.update_batch.id}"
}

resource "aws_apigatewayv2_route" "update_batch_status" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /api/v1/batches/{id}/status"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.update_batch_status.id}"
}

# ---------------------------------------------------------------------------
# EventBridge Scheduler — nightly auto-close expired batches
# ---------------------------------------------------------------------------
resource "aws_iam_role" "scheduler_exec" {
  name = "coquito-scheduler-exec-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "coquito-scheduler-invoke-${var.environment}"
  role = aws_iam_role.scheduler_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.close_expired_batches.arn
    }]
  })
}

resource "aws_scheduler_schedule" "close_expired_batches" {
  name       = "coquito-close-expired-batches-${var.environment}"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(5 0 * * ? *)"

  target {
    arn      = aws_lambda_function.close_expired_batches.arn
    role_arn = aws_iam_role.scheduler_exec.arn
  }
}

# ---------------------------------------------------------------------------
# CloudWatch log groups — chef batch management
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "get_me" {
  name              = "/aws/lambda/coquito-get-me"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "list_batches" {
  name              = "/aws/lambda/coquito-list-batches"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "create_batch" {
  name              = "/aws/lambda/coquito-create-batch"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "update_batch" {
  name              = "/aws/lambda/coquito-update-batch"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "update_batch_status" {
  name              = "/aws/lambda/coquito-update-batch-status"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "close_expired_batches" {
  name              = "/aws/lambda/coquito-close-expired-batches"
  retention_in_days = 30
}

# ---------------------------------------------------------------------------
# Lambda functions — chef variety management (protected, chef-role required)
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "chef_list_varieties" {
  function_name    = "coquito-chef-list-varieties"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.chef_list_varieties.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "chef_create_variety" {
  function_name    = "coquito-chef-create-variety"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.chef_create_variety.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

resource "aws_lambda_function" "chef_update_variety" {
  function_name    = "coquito-chef-update-variety"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = local.lambda_runtime
  handler          = "${local.lambda_handler_prefix}.chef_update_variety.handler"
  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)
  timeout          = 10
  architectures    = local.lambda_architectures
  layers           = [aws_lambda_layer_version.deps.arn]
  environment {
    variables = {
      ENVIRONMENT              = var.environment
      DYNAMODB_REQUESTS_TABLE  = var.dynamodb_requests_table
      DYNAMODB_BATCHES_TABLE   = var.dynamodb_batches_table
      DYNAMODB_VARIETIES_TABLE = var.dynamodb_varieties_table
    }
  }
}

# ---------------------------------------------------------------------------
# Integrations — chef variety management
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_integration" "chef_list_varieties" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.chef_list_varieties.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "chef_create_variety" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.chef_create_variety.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "chef_update_variety" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.chef_update_variety.invoke_arn
  payload_format_version = "2.0"
}

# ---------------------------------------------------------------------------
# Routes — chef variety management (protected, Lambda authorizer)
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_route" "chef_list_varieties" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /api/v1/chef/varieties"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.chef_list_varieties.id}"
}

resource "aws_apigatewayv2_route" "chef_create_variety" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /api/v1/chef/varieties"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.chef_create_variety.id}"
}

resource "aws_apigatewayv2_route" "chef_update_variety" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /api/v1/chef/varieties/{id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.main.id
  target             = "integrations/${aws_apigatewayv2_integration.chef_update_variety.id}"
}

# ---------------------------------------------------------------------------
# CloudWatch log groups — chef variety management
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "chef_list_varieties" {
  name              = "/aws/lambda/coquito-chef-list-varieties"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "chef_create_variety" {
  name              = "/aws/lambda/coquito-chef-create-variety"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "chef_update_variety" {
  name              = "/aws/lambda/coquito-chef-update-variety"
  retention_in_days = 30
}
