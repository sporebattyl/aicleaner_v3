/**
 * Email validation utility function
 * 
 * Validates email addresses using a basic regex pattern that checks for:
 * - At least one character before the @ symbol
 * - Exactly one @ symbol  
 * - At least one character after the @ symbol
 * - A domain with at least one dot and extension
 * 
 * Note: This is a basic validation suitable for most use cases. For comprehensive
 * email validation according to RFC 5322, consider using a specialized library.
 * 
 * @param {string} email - The email address to validate
 * @returns {boolean} True if the email format is valid, false otherwise
 * 
 * @example
 * // Valid email addresses
 * validateEmail('user@example.com');        // returns true
 * validateEmail('test.email@domain.org');   // returns true
 * validateEmail('admin@subdomain.site.co'); // returns true
 * 
 * @example
 * // Invalid email addresses
 * validateEmail('invalid-email');           // returns false
 * validateEmail('user@');                   // returns false
 * validateEmail('@domain.com');             // returns false
 * validateEmail('user@domain');             // returns false
 * 
 * @example
 * // Edge cases
 * validateEmail(null);                      // returns false
 * validateEmail(undefined);                 // returns false
 * validateEmail('');                        // returns false
 * validateEmail(123);                       // returns false
 */
function validateEmail(email) {
    // Handle edge cases: null, undefined, empty string, or non-string types
    if (!email || typeof email !== 'string') {
        return false;
    }
    
    // Trim whitespace to handle accidental leading/trailing spaces
    const trimmedEmail = email.trim();
    
    // Check if empty after trimming
    if (trimmedEmail.length === 0) {
        return false;
    }
    
    // Basic email regex pattern
    // Pattern explanation:
    // ^         - Start of string
    // [^\s@]+   - One or more characters that are not whitespace or @
    // @         - Literal @ symbol
    // [^\s@]+   - One or more characters that are not whitespace or @
    // \.        - Literal dot
    // [^\s@]+   - One or more characters that are not whitespace or @
    // $         - End of string
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    return emailRegex.test(trimmedEmail);
}

// Export the function for use in other modules
module.exports = validateEmail;

// For ES6 modules, you can also export as:
// export default validateEmail;
// export { validateEmail };