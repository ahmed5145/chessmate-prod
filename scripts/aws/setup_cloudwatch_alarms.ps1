# Create ChessMate production CloudWatch alarms (EB CPU, ALB 5xx, RDS connections).
# Prerequisite: attach scripts/aws/iam-cloudwatch-alarms-policy.json to the IAM user (or run as admin).
#
# PowerShell (NOT CMD "set"):
#   $env:AWS_PROFILE = "chessmate-deploy"
#   $env:ALARM_EMAIL = "you@example.com"
#   .\scripts\aws\setup_cloudwatch_alarms.ps1
#
# Or pass email directly:
#   .\scripts\aws\setup_cloudwatch_alarms.ps1 -AlarmEmail "you@example.com"

param(
    [string]$Region = "us-east-2",
    [string]$EnvironmentName = "Chessmate-env-2",
    [string]$DbInstanceId = "chessmate-db",
    [string]$LoadBalancerSuffix = "app/awseb--AWSEB-88ETMTsRQAaW/ecbbdfc2fbd65953",
    [string]$AlarmEmail = "",
    [string]$SnsTopicName = "chessmate-prod-alarms",
    [switch]$SkipSns
)

$ErrorActionPreference = "Stop"

if (-not $AlarmEmail) {
    $AlarmEmail = $env:ALARM_EMAIL
}

if (-not $SkipSns -and -not $AlarmEmail) {
    Write-Host ""
    Write-Host "Missing alarm email."
    Write-Host "In PowerShell use:"
    Write-Host '  $env:ALARM_EMAIL = "ahmedmohamed200354@gmail.com"'
    Write-Host "Or:"
    Write-Host '  .\scripts\aws\setup_cloudwatch_alarms.ps1 -AlarmEmail "ahmedmohamed200354@gmail.com"'
    Write-Host ""
    Write-Host 'Note: CMD "set ALARM_EMAIL=..." does NOT set PowerShell environment variables.'
    Write-Error "Set ALARM_EMAIL or pass -AlarmEmail, or use -SkipSns."
}

Write-Host "Region: $Region"
if ($AlarmEmail) {
    Write-Host "Alarm email: $AlarmEmail"
}

$accountId = (aws sts get-caller-identity --query Account --output text).Trim()
$topicArn = "arn:aws:sns:${Region}:${accountId}:${SnsTopicName}"
$actionArgs = @()

if (-not $SkipSns) {
    $existingTopic = aws sns list-topics --region $Region --query "Topics[?TopicArn=='$topicArn'].TopicArn" --output text
    if (-not $existingTopic) {
        Write-Host "Creating SNS topic $SnsTopicName ..."
        aws sns create-topic --name $SnsTopicName --region $Region | Out-Null
        aws sns subscribe --topic-arn $topicArn --protocol email --notification-endpoint $AlarmEmail --region $Region | Out-Null
        Write-Host "SNS subscription pending. Confirm the email AWS sent to $AlarmEmail"
    } else {
        Write-Host "SNS topic already exists: $topicArn"
    }
    $actionArgs = @("--alarm-actions", $topicArn, "--ok-actions", $topicArn)
}

function Put-Alarm {
    param(
        [string]$Name,
        [string]$Namespace,
        [string]$MetricName,
        [string]$DimensionArg,
        [double]$Threshold,
        [string]$ComparisonOperator,
        [int]$Period = 300,
        [int]$EvaluationPeriods = 2,
        [string]$Statistic = "Average",
        [string]$TreatMissingData = "notBreaching",
        [string]$Unit = $null,
        [string]$AlarmDescription
    )

    $awsCliArgs = @(
        "cloudwatch", "put-metric-alarm",
        "--region", $Region,
        "--alarm-name", $Name,
        "--alarm-description", $AlarmDescription,
        "--namespace", $Namespace,
        "--metric-name", $MetricName,
        "--dimensions", $DimensionArg,
        "--period", $Period,
        "--evaluation-periods", $EvaluationPeriods,
        "--threshold", $Threshold,
        "--comparison-operator", $ComparisonOperator,
        "--statistic", $Statistic,
        "--treat-missing-data", $TreatMissingData
    )
    if ($Unit) {
        $awsCliArgs += @("--unit", $Unit)
    }
    if ($actionArgs.Count -gt 0) {
        $awsCliArgs += $actionArgs
    }

    Write-Host "Putting alarm $Name ..."
    & aws @awsCliArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create alarm $Name (exit $LASTEXITCODE)"
    }
}

Put-Alarm `
    -Name "Chessmate-EB-CPU-High" `
    -Namespace "AWS/ElasticBeanstalk" `
    -MetricName "CPUUtilization" `
    -DimensionArg "Name=EnvironmentName,Value=$EnvironmentName" `
    -Threshold 80 `
    -ComparisonOperator "GreaterThanThreshold" `
    -Period 300 `
    -EvaluationPeriods 3 `
    -Statistic "Average" `
    -Unit "Percent" `
    -AlarmDescription "EB environment CPU above 80% for 15 minutes"

Put-Alarm `
    -Name "Chessmate-ALB-Target-5xx" `
    -Namespace "AWS/ApplicationELB" `
    -MetricName "HTTPCode_Target_5XX_Count" `
    -DimensionArg "Name=LoadBalancer,Value=$LoadBalancerSuffix" `
    -Threshold 10 `
    -ComparisonOperator "GreaterThanOrEqualToThreshold" `
    -Period 300 `
    -EvaluationPeriods 1 `
    -Statistic "Sum" `
    -AlarmDescription "ALB target returned 10+ 5xx responses in 5 minutes"

Put-Alarm `
    -Name "Chessmate-RDS-Connections-High" `
    -Namespace "AWS/RDS" `
    -MetricName "DatabaseConnections" `
    -DimensionArg "Name=DBInstanceIdentifier,Value=$DbInstanceId" `
    -Threshold 75 `
    -ComparisonOperator "GreaterThanThreshold" `
    -Period 300 `
    -EvaluationPeriods 2 `
    -Statistic "Average" `
    -AlarmDescription "RDS connection count above 75 (db.t3.micro headroom)"

Write-Host ""
Write-Host "Done. Verify in AWS Console -> CloudWatch -> Alarms."
