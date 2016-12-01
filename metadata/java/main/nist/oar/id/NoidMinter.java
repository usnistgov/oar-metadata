package nist.oar.id;

import java.util.HashMap;
import java.util.Arrays;

/**
 * An IDMinter that creates NOID-compliant identifiers
 * 
 * NOID stands for Nice Opaque Identifier.  With this convention, identifier 
 * strings contain only numbers and lower-case letters, excluding vowels and 
 * the letter 'l'.  This convention is intented to maintain identifier 
 * opaqueness while avoiding characters that are prone to human transcription 
 * errors.  NOIDs may optionally include a single trailing "check character"; 
 * this is essentially a 1-byte check-sum of the identifier.  It allows 
 * applications to inform users that an unrecognized identifier is actually 
 * invalid, possibly due to a transcription error.  
 * 
 * The inner class NoidFactory is a port of the pynoid Python library which 
 * implements the NOID convention.  In this implementation, identifiers are 
 * created according to a template or <i>mask</i> given at construction (see
 * {@link #NoidMinter(String,int,IDRegistry)} for syntax details).  This 
 * mask defines a sequence of potential identifiers; to create an ID, one 
 * provides a sequence number to retrieve the associated ID.  This class 
 * keeps a sequence number, initialized at construction, which represents the 
 * next ID to be issued; it is incremented with each call to 
 * {@link #mint(HashMap<String, Object>}.
 */
public class NoidMinter implements IDMinter {

    /**
     * the factory that implements the NOID convention which is used 
     * to create identifiers
     */
    protected NoidFactory fact = null;

    /**
     * the starting sequence number used for creating a series of identifiers.
     * This value is incremented with each identifier minted. 
     */
    protected int nextn = 1;

    /**
     * An IDRegistry used to keep track of identifiers already issued.
     */
    protected IDRegistry reg = null;

    /**
     * Create the minter
     * 
     * IDs issued by this minter have a form specified by a template that 
     * is defined by the pynoid module.  In general, a template has the 
     * following form, expressed as a regular expression:
     * 
     * (.+\.)?[zrs]?[de]+k?
     * 
     * The template breaks down into the following components:
     * 
     * (.+\.) -- This portion represents an optional prefix, minus the 
     * '.' delimiter, that all emitted IDs will start with.  
     * [de]+  -- This portion is the core of the pattern and is represented 
     * by a sequence of 'd' and 'e' characters; the total number 
     * specifies the minimal number of characters that will appear 
     * after the optional prefix.  'd' means only a numerical digit
     * will appear in that position; 'e' means that either a digit
     * or a letter can appear.  
     * [zrs]? -- The sequence of d/e characters can be preceded by a 'z', 
     * 'r', or 's' character.  If this character is a 'z',
     * then the number of characters will appear after the prefix 
     * will be expanded as needed.  Without this 'z', the minter
     * would eventually run out of IDs.  The expanded digits will
     * be of the type given by the first 'd' or 'e' character.  
     * k?     -- If the template ends with a 'k' character, the emitted ID
     * will be appended with an extra "check character" (see 
     * description in the class documentation).  
     * 
     * @param template    a pynoid compliant mask; see explanation above
     * @param firstseq    the sequence number to start with; when no 
     *                    registry is used (and the default is provided)
     *                    it is assumed that identifiers have already been 
     *                    issued for sequence numbers less than this value.
     * @param registry IDRegistry:  The registry to use for keeping track of 
     *                    previously issued IDs.
     */
    public NoidMinter(String template, int firstseq, IDRegistry registry) {
        fact = NoidFactory((template == null) ? 'zeeek' : template);
        nextn = (firstseq < 0) ? 1 : firstseq;
        reg = (registry == null) ? new SeqReg(nextn-1, fact) : registry;
    }

    /**
     * Create the minter.  
     *
     * A default internal non-peristent registry will be used to keep track 
     * of issued identifiers.
     * 
     * @param template    a pynoid compliant mask; see 
     *                    {@link #NoidMinter(String,int,IDRegistry)} for
     *                    a description of the mask template syntax.
     * @param firstseq    the sequence number to start with; when no 
     *                    registry is used (and the default is provided)
     *                    it is assumed that identifiers have already been 
     *                    issued for sequence numbers less than this value.
     */
    public NoidMinter(String template, int firstseq) {
        this(template, firstseq, null);
    }

    /**
     * Create the minter.  
     *
     * The first ID minted will correspond to the sequence number 1.  
     * A default internal non-peristent registry will be used to keep track
     * of issued identiifiers.
     * 
     * @param template    a pynoid compliant mask; see 
     *                    {@link #NoidMinter(String,int,IDRegistry)} for
     *                    a description of the mask template syntax.
     */
    public NoidMinter(String template) {
        this(template, 1, null);
    }

    /**
     * Create the minter.  
     *
     * Identifiers minted will match the template, "zeeek" (see 
     * {@link #NoidMinter(String,int,IDRegistry)} to template syntax
     * details).  The first ID minted will correspond to the sequence 
     * number 1.  A default internal non-peristent registry will be used
     * to keep track of issued identifiers.
     */
    public NoidMinter() {
        this(template, 1, null);
    }

    /**
     * return an available identifier string.  
     * 
     * Whether the data parameter is supported depends on the support 
     * provided by the IDRegistry instance provided at construction.  
     * The default registry (used if no registry was provided) does not 
     * support the data parameter; if provided, it will be ignored.  
     * 
     * @param data    any data to associate with the identifier.  (See
     *                note above about its support.)
     * 
     */
    public String mint(HashMap<String, Object> data = null) {
        out = fact.idFor(nextn++);
        while (issued(out)) {
            out = fact.idFor(nextn++);
        }
        reg.registerID(out, data);
        return out;
    }

    /**
     * return true if the given identifier string is a recognized one that 
     * has been previously issued.
     */
    public boolean issued(String id) {
        return self.registry.registered(id)
    }

    /**
     * return the data associated with the given ID.  Null is returned if 
     * no data was associated with the ID when it was minted (or data 
     * association is not supported).  
     */
    public HashMap<String, Object> dataFor(String id) {
        return null;
    }

    /**
     * a default IDRegistry that assumes all issued IDs have an associated 
     * sequence number smaller than or equal to a maximum value.
     */
    public class SeqReg implements IDRegistry {

        /**
         * create the registry.  The NoidFactory is used to determine the 
         * sequence number associated with given IDs.
         */
        public SeqReg(int initn, NoidFactory fact) {
        }
    }

    /**
     * A class that actually implements the NOID convention as specified 
     * by a given mask.  See {@link #NoidMinter(String,int,IDRegistry)} 
     * for syntax details.
     */
    public class NoidFactory {

        public static String XDIGIT = "0123456789bcdfghjkmnpqrstvwxz";

        private boolean include_check_digit = false;
        private boolean expand = false;
        private String prefix = "";
        private char[] digtype = ['e', 'e', 'e'];

        public NoidFactory(String mask) {
            parseMask(mask);
        }

        protected void parseMask(String mask) {

            // look for a prefix
            int p = -1;
            if ((p = mask.lastIndexOf('.')) >= 0) {
                prefix = mask.substring(0,p);
                mask = mask.substring(p+1);
            }

            if (mask.charAt(mask.length()-1) == 'k') {
                include_check_digit = true;
                mask = mask.substring(0, len(mask.length()-1));
            }

            if ("rsz".contains(mask.charAt(0))) {
                // we ignore 's' or 'z'; unimplemented
                if (mask.charAt(0) == 'z') 
                    expand = true;
                mask = mask.substring(1);
            }

            // check the core mask for illegal characters
            digtype = mask.toCharArray()
            for(int i=0; i < len(mask); i++)
                if (digtype[i] != 'd' and digtype[i] != 'e')
                    throw new IllegalArgumentException(
                        "illegal mask character provided (not 'd' or 'e'): " +
                        digtype[i] + " in " + mask);

        }

        public String idFor(int seq) {
            String id = prefix + _buildIdCore(seq);
            if (include_check_digit) 
                id += Character.toString(_checkDigit(id));
            return id
        }

        private String _buildIdCore(int seq) {
            char m;
            int div = 1, val = 0;
            StringBuilder sb = new StringBuilder();

            for(int i=len(digtype)-1; i >= 0; i--) {
                div = _base(digtype[i]);
                try {
                    val = seq % div;
                    seq /= div;
                } catch (ArithmeticException ex) {
                    continue;
                }
                sb.append(XDIGIT.charAt(val));
            }
            
            // that's i
            if (expand) {
                char c = digtype[0];
                div = _base(digtype[0])
                while (seq > 0) {
                    try {
                        val = seq % div;
                        seq /= div;
                    } catch (ArithmeticException ex) {
                    throw new IllegalArgumentException(
                       "illegal mask character (not 'd' or 'e'): " + digtype[i]);
                    }
                    sb.append(XDIGIT.charAt(value));
                }
            }

            if (seq > 0)
                throw new IndexOutOfBoundsException("Requested sequence number is out of range of identifier set");

            return sb.reverse().toString();
        }

        private char _checkDigit(String id) {
            int p = -1;
            if ((p = id.indexOf(':')) >= 0)
                id = id.substring(p+1);

            int tot = 0;
            for (int i=0; i < len(id); i++) {
                p = _ordinal(id.charAt(i));
                tot += p * (i+1);
            }
            return XDIGIT.charAt( tot % XDIGIT.length() );
        }

        private int _ordinal(char c) {
            int out = XDIGIT.indexOf(c);
            if (out < 0) out = 0;
            return out;
        }
        
        private int _base(char type) {
            if (type == 'e') return XDIGIT.length();
            if (type == 'd') return 10;
            return 0;
        }

        public boolean validate(String id) {
            return _checkDigit(id.substring(0, id.length()-1)) ==
                                                     id.charAt(id.length()-1);
        }

        public int seqFor(String id) {
        }
    }

}
