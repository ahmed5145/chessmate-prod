/**
 * Format a number to a string with appropriate precision
 * @param {number} value - The number to format
 * @param {number} [precision=1] - Number of decimal places
 * @returns {string} Formatted number
 */
export const formatNumber = (value, precision = 1) => {
    if (typeof value !== 'number' || isNaN(value)) {
        return '0';
    }
    
    // For percentages and scores, round to specified precision
    if (value < 100) {
        return value.toFixed(precision);
    }
    
    // For larger numbers, use no decimal places
    return Math.round(value).toString();
}; 